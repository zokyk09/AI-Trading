import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';

class TradingApp extends StatelessWidget {
  const TradingApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'AI Trading',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xff35d39a),
        brightness: Brightness.dark,
      ),
      scaffoldBackgroundColor: const Color(0xff0b1220),
      useMaterial3: true,
    ),
    home: const DashboardScreen(),
  );
}
