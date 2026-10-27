import 'dart:async';
import 'package:flutter/material.dart';

import '../models/broker_profile.dart';
import '../services/local_settings.dart';
import '../services/trading_api.dart';
import '../widgets/info_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final TradingApi _api = TradingApi();
  LocalSettings? _settings;
  Timer? _refreshTimer;
  Map<String, dynamic> _status = {}, _account = {}, _signal = {}, _auto = {};
  List<dynamic> _positions = [], _history = [];
  bool _loading = false;
  String? _error;

  String get _brokerName => _settings?.selectedBroker ?? 'Broker';
  String get _apiUrl => _settings?.apiBaseUrl ?? '';
  bool get _demoAccount =>
      _account['connected'] == true && _account['trade_mode'] == 0;
  bool get _autoEnabled => _auto['enabled'] == true;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    final settings = await LocalSettings.load();
    if (!mounted) return;
    _api.baseUrl = settings.apiBaseUrl;
    setState(() => _settings = settings);
    await _refresh();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _refresh(silent: true),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _api.close();
    super.dispose();
  }

  Future<void> _refresh({bool silent = false}) async {
    if (!mounted || _settings == null || _loading) return;
    if (!silent) setState(() => _loading = true);
    try {
      final result = await Future.wait([
        _api.get('/api/status'),
        _api.get('/api/account'),
        _api.get('/api/signal'),
        _api.get('/api/positions'),
        _api.get('/api/auto'),
        _api.get('/api/history'),
      ]);
      if (!mounted) return;
      setState(() {
        _status = result[0];
        _account = result[1];
        _signal = result[2];
        _positions = (result[3]['positions'] as List?) ?? [];
        _auto = result[4];
        _history = (result[5]['history'] as List?) ?? [];
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _friendlyError(e);
        _loading = false;
      });
    }
  }

  String _friendlyError(Object error) {
    final text = error.toString();
    if (text.contains('Isi alamat home server')) return text;
    if (text.contains('No route to host') ||
        text.contains('Connection refused') ||
        text.contains('Failed host lookup')) {
      return 'Home server tidak terjangkau. Pastikan HP dan server satu Wi-Fi, URL/IP benar, backend berjalan dengan --host 0.0.0.0 --port 8000, dan Windows Firewall mengizinkan TCP 8000. URL: $_apiUrl';
    }
    return 'Gagal mengambil data dari backend: $text';
  }

  Future<bool> _confirm({
    required String title,
    required String message,
    String confirmText = 'Lanjutkan',
  }) async =>
      await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Batal'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(confirmText),
            ),
          ],
        ),
      ) ??
      false;

  Future<void> _toggleAuto() async {
    final enable = !_autoEnabled;
    if (enable && !_demoAccount) {
      _showMessage('Robot hanya dapat dimulai saat akun DEMO MT5 terhubung.');
      return;
    }
    if (enable) {
      final confirmed = await _confirm(
        title: 'Aktifkan robot demo?',
        message:
            'Robot dapat mengirim order otomatis XAUUSD. Parameter saat ini: volume ${_auto['volume'] ?? '0.01'} lot, SL ${_auto['sl'] ?? '1.00'}, TP ${_auto['tp'] ?? '2.00'}, confidence minimum ${_auto['confidence'] ?? '55'}%. Pastikan MT5 login ke akun DEMO.',
        confirmText: 'START DEMO',
      );
      if (!confirmed) return;
    }
    try {
      final result = await _api.post('/api/auto', body: {'enabled': enable});
      _showMessage(result['message']?.toString() ?? 'Status robot diperbarui.');
      await _refresh();
    } catch (e) {
      _showMessage(_friendlyError(e));
    }
  }

  Future<void> _sendManualOrder(String side) async {
    if (!_demoAccount) {
      _showMessage('Order hanya dapat dikirim saat akun DEMO MT5 terhubung.');
      return;
    }
    final confirmed = await _confirm(
      title: 'Kirim order $side?',
      message:
          '$side ${_signal['symbol'] ?? 'XAUUSD'} · 0,01 lot\nSL jarak harga ${_auto['sl'] ?? '1.00'} · TP ${_auto['tp'] ?? '2.00'}\n\nOrder langsung dikirim ke akun DEMO MT5.',
      confirmText: 'KIRIM $side DEMO',
    );
    if (!confirmed) return;
    try {
      final result = await _api.post(
        '/api/order',
        body: {
          'symbol': _signal['symbol'] ?? 'XAUUSD',
          'side': side,
          'volume': 0.01,
        },
      );
      _showMessage(
        result['success'] == true
            ? '${result['message']} · ticket ${result['order']}'
            : result['message']?.toString() ?? 'Order ditolak.',
      );
      await _refresh();
    } catch (e) {
      _showMessage(_friendlyError(e));
    }
  }

  void _showMessage(String message) {
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  Future<void> _editServer() async {
    final controller = TextEditingController(text: _apiUrl);
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Koneksi home server'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            labelText: 'URL backend',
            hintText: 'http://192.168.1.20:8000',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Simpan'),
          ),
        ],
      ),
    );
    if (value == null || value.isEmpty || _settings == null) return;
    _settings!.apiBaseUrl = value;
    _api.baseUrl = value;
    await _settings!.save();
    if (mounted) setState(() {});
    await _refresh();
  }

  Future<void> _brokerMenu() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Broker & akun demo',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () async {
                      Navigator.pop(sheetContext);
                      await _addBroker();
                    },
                    icon: const Icon(Icons.add),
                    tooltip: 'Tambah profil',
                  ),
                ],
              ),
              const Text(
                'Broker aktif mengikuti terminal MT5 yang login pada home server.',
                style: TextStyle(color: Color(0xff9eabc1), fontSize: 12),
              ),
              ...?_settings?.brokers.map(
                (broker) => ListTile(
                  leading: const Icon(Icons.account_balance),
                  title: Text(broker.name),
                  subtitle: Text(
                    'DEMO${broker.server.isEmpty ? '' : ' · ${broker.server}'}',
                  ),
                  trailing: broker.name == _settings?.selectedBroker
                      ? const Icon(Icons.check_circle, color: Color(0xff35d39a))
                      : null,
                  onTap: () async {
                    _settings!.selectedBroker = broker.name;
                    await _settings!.save();
                    if (mounted) setState(() {});
                    if (sheetContext.mounted) Navigator.pop(sheetContext);
                  },
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _addBroker() async {
    final name = TextEditingController();
    final server = TextEditingController();
    final broker = await showDialog<BrokerProfile>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Tambah profil broker'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Nama broker'),
            ),
            TextField(
              controller: server,
              decoration: const InputDecoration(
                labelText: 'Server MT5 (opsional)',
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Password tidak disimpan di HP. Login ke akun demo pada MT5 home server.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () {
              if (name.text.trim().isNotEmpty) {
                Navigator.pop(
                  context,
                  BrokerProfile(
                    name: name.text.trim(),
                    server: server.text.trim(),
                  ),
                );
              }
            },
            child: const Text('Tambah'),
          ),
        ],
      ),
    );
    if (broker == null || _settings == null) return;
    final index = _settings!.brokers.indexWhere(
      (item) => item.name.toLowerCase() == broker.name.toLowerCase(),
    );
    if (index < 0) {
      _settings!.brokers.add(broker);
    } else {
      _settings!.brokers[index] = broker;
    }
    _settings!.selectedBroker = broker.name;
    await _settings!.save();
    if (mounted) setState(() {});
  }

  Widget _section(String title, List<Widget> rows, IconData icon) => InfoCard(
    title: title,
    icon: icon,
    child: Column(children: rows),
  );

  Widget _positionList() => _positions.isEmpty
      ? const Text('Tidak ada posisi terbuka.')
      : Column(
          children: _positions.take(10).map((item) {
            final p = Map<String, dynamic>.from(item as Map);
            return Column(
              children: [
                DataRowView(
                  '${p['symbol']} · ${p['type'] == 0 ? 'BUY' : 'SELL'}',
                  '${p['volume']} lot',
                ),
                DataRowView(
                  'Harga masuk / P&L',
                  '${p['price_open']} / ${p['profit']}',
                ),
                const Divider(height: 12),
              ],
            );
          }).toList(),
        );

  Widget _historyList() => _history.isEmpty
      ? const Text('Belum ada transaksi 30 hari terakhir.')
      : Column(
          children: _history.take(10).map((item) {
            final trade = Map<String, dynamic>.from(item as Map);
            return Column(
              children: [
                DataRowView(
                  '${trade['symbol']} · ${trade['type']}',
                  '${trade['volume']} lot',
                ),
                DataRowView('${trade['time']}', 'P&L ${trade['profit']}'),
                const Divider(height: 12),
              ],
            );
          }).toList(),
        );

  @override
  Widget build(BuildContext context) {
    final autoOn = _autoEnabled;
    return Scaffold(
      drawer: Drawer(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              DrawerHeader(
                decoration: const BoxDecoration(color: Color(0xff151f32)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    const Icon(
                      Icons.candlestick_chart,
                      color: Color(0xff35d39a),
                      size: 38,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'AI Trading',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      '$_brokerName · DEMO',
                      style: const TextStyle(color: Color(0xff9eabc1)),
                    ),
                  ],
                ),
              ),
              ListTile(
                leading: const Icon(Icons.dashboard),
                title: const Text('Dashboard'),
                onTap: () => Navigator.pop(context),
              ),
              ListTile(
                leading: const Icon(Icons.account_balance),
                title: const Text('Broker & akun'),
                subtitle: Text(_brokerName),
                onTap: () {
                  Navigator.pop(context);
                  _brokerMenu();
                },
              ),
              ListTile(
                leading: const Icon(Icons.dns),
                title: const Text('Koneksi home server'),
                subtitle: Text(_apiUrl.isEmpty ? 'Belum diatur' : _apiUrl),
                onTap: () {
                  Navigator.pop(context);
                  _editServer();
                },
              ),
              ListTile(
                leading: const Icon(Icons.refresh),
                title: const Text('Muat ulang data'),
                onTap: () {
                  Navigator.pop(context);
                  _refresh();
                },
              ),
              const Spacer(),
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Mode DEMO · Password broker tetap di terminal MT5 home server.',
                  style: TextStyle(color: Color(0xff9eabc1), fontSize: 12),
                ),
              ),
            ],
          ),
        ),
      ),
      appBar: AppBar(
        title: Text('AI Trading · $_brokerName Demo'),
        actions: [
          IconButton(
            tooltip: 'Broker',
            onPressed: _brokerMenu,
            icon: const Icon(Icons.account_balance),
          ),
          IconButton(
            tooltip: 'Server',
            onPressed: _editServer,
            icon: const Icon(Icons.settings_ethernet),
          ),
          IconButton(
            tooltip: 'Muat ulang',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 28),
          children: [
            if (_error != null)
              Card(
                color: const Color(0xff542a35),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(_error!),
                ),
              ),
            _section('Koneksi server & MT5', [
              DataRowView(
                'API',
                _apiUrl.isEmpty ? 'Atur alamat server' : _apiUrl,
              ),
              DataRowView('MT5', _status['message'] ?? 'Belum terhubung'),
              DataRowView(
                'Izin trading',
                _status['trade_allowed'] == true ? 'Aktif' : 'Nonaktif',
              ),
              if (_loading) const LinearProgressIndicator(),
            ], Icons.cloud_done),
            _section('Akun $_brokerName', [
              DataRowView(
                'Status',
                _account['connected'] == true ? 'Terhubung' : 'Belum terhubung',
              ),
              DataRowView(
                'Broker dari MT5',
                _account['company'] ?? _account['server'],
              ),
              DataRowView('Login', _account['login']),
              DataRowView('Saldo', _account['balance']),
              DataRowView('Equity', _account['equity']),
              DataRowView('Profit', _account['profit']),
              DataRowView('Mata uang', _account['currency']),
            ], Icons.account_balance_wallet),
            _section('Sinyal ${_signal['symbol'] ?? 'XAUUSD'}', [
              DataRowView('Timeframe', _signal['timeframe']),
              DataRowView('Harga', _signal['price']),
              DataRowView('Sinyal', _signal['signal']),
              DataRowView(
                'BUY / SELL confidence',
                '${_signal['buy_probability'] ?? '-'}% / ${_signal['sell_probability'] ?? '-'}%',
              ),
              DataRowView(
                'RSI · EMA20 · EMA50',
                '${_signal['RSI'] ?? '-'} · ${_signal['EMA20'] ?? '-'} · ${_signal['EMA50'] ?? '-'}',
              ),
            ], Icons.show_chart),
            InfoCard(
              title: 'Order manual demo',
              icon: Icons.swap_horiz,
              child: Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: _demoAccount
                          ? () => _sendManualOrder('BUY')
                          : null,
                      child: const Text('BUY 0,01'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xffe25562),
                      ),
                      onPressed: _demoAccount
                          ? () => _sendManualOrder('SELL')
                          : null,
                      child: const Text('SELL 0,01'),
                    ),
                  ),
                ],
              ),
            ),
            InfoCard(
              title: 'Robot otomatis',
              icon: Icons.smart_toy,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DataRowView('Mode', _auto['mode'] ?? 'DEMO_ONLY'),
                  DataRowView('Status', autoOn ? 'AKTIF' : 'STOP'),
                  DataRowView(
                    'Volume · confidence',
                    '${_auto['volume'] ?? '-'} lot · ${_auto['confidence'] ?? '-'}%',
                  ),
                  DataRowView(
                    'Stop loss · take profit',
                    '${_auto['sl'] ?? '-'} · ${_auto['tp'] ?? '-'}',
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: autoOn
                            ? const Color(0xffe25562)
                            : const Color(0xff35b982),
                        foregroundColor: Colors.white,
                      ),
                      onPressed: autoOn || _demoAccount ? _toggleAuto : null,
                      icon: Icon(autoOn ? Icons.stop : Icons.play_arrow),
                      label: Text(autoOn ? 'STOP ROBOT' : 'START ROBOT DEMO'),
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'START dapat mengirim order otomatis. Akun DEMO MT5 wajib terhubung.',
                    style: TextStyle(color: Color(0xff9eabc1), fontSize: 12),
                  ),
                ],
              ),
            ),
            InfoCard(
              title: 'Posisi terbuka (${_positions.length})',
              icon: Icons.list_alt,
              child: _positionList(),
            ),
            InfoCard(
              title: 'Riwayat transaksi · 30 hari',
              icon: Icons.history,
              child: _historyList(),
            ),
            const Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'Profil broker hanya label. Perpindahan broker dilakukan dengan login ke akun DEMO pada MT5 home server. Gunakan LAN lokal; login Cloudflare Access untuk API Flutter belum diaktifkan.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xff9eabc1), fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
