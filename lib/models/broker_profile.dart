class BrokerProfile {
  const BrokerProfile({
    required this.name,
    this.server = '',
    this.mode = 'DEMO',
  });

  final String name;
  final String server;
  final String mode;

  Map<String, String> toJson() => {
    'name': name,
    'server': server,
    'mode': mode,
  };

  factory BrokerProfile.fromJson(Map<dynamic, dynamic> json) => BrokerProfile(
    name: json['name']?.toString() ?? 'Broker MT5',
    server: json['server']?.toString() ?? '',
    mode: json['mode']?.toString() ?? 'DEMO',
  );

  static List<BrokerProfile> defaults() => const [
    BrokerProfile(name: 'Finex'),
    BrokerProfile(name: 'Broker MT5 lainnya'),
  ];
}
