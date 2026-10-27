import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ai_trading/app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('shows the trading dashboard shell', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const TradingApp());
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.textContaining('AI Trading'), findsOneWidget);
  });
}
