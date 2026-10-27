import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/broker_profile.dart';

class LocalSettings {
  LocalSettings({
    required this.apiBaseUrl,
    required this.selectedBroker,
    required this.brokers,
  });

  String apiBaseUrl;
  String selectedBroker;
  List<BrokerProfile> brokers;

  static Future<LocalSettings> load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('broker_profiles');
    var brokers = BrokerProfile.defaults();
    if (saved != null) {
      try {
        brokers = (jsonDecode(saved) as List)
            .map((item) => BrokerProfile.fromJson(item as Map))
            .toList();
      } catch (_) {
        brokers = BrokerProfile.defaults();
      }
    }
    final selected = prefs.getString('selected_broker') ?? 'Finex';
    return LocalSettings(
      apiBaseUrl: prefs.getString('api_base_url') ?? '',
      selectedBroker: brokers.any((b) => b.name == selected)
          ? selected
          : brokers.first.name,
      brokers: brokers,
    );
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', apiBaseUrl);
    await prefs.setString('selected_broker', selectedBroker);
    await prefs.setString(
      'broker_profiles',
      jsonEncode(brokers.map((broker) => broker.toJson()).toList()),
    );
  }
}
