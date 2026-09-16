// בדיקת המנוע: Skia קוראת את רוחב ה-advance מן ה-CFF, ואילו כל בדיקה
// בצד פייתון קוראת אותו מ-hmtx. באג ה-575 חי בפער הזה, ולכן הבדיקה כאן
// אינה כפילות אלא הכיסוי היחיד לצד שבו התוכנה באמת פוגשת את הגופן.

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:otzaria_ashurit/otzaria_ashurit.dart';

import 'expected.g.dart';

const double kEm = 1000;

Future<void> loadFamily(String family, List<String> files) async {
  final loader = FontLoader(family);
  for (final file in files) {
    loader.addFont(rootBundle.load('packages/otzaria_ashurit/$file'));
  }
  await loader.load();
}

double advance(String text, String family,
    {double size = kEm, FontWeight weight = FontWeight.normal}) {
  final painter = TextPainter(
    text: TextSpan(
      text: text,
      style: TextStyle(fontFamily: family, fontSize: size, fontWeight: weight),
    ),
    textDirection: TextDirection.rtl,
  )..layout();
  return painter.width;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await loadFamily(ashuritFamily,
        ['OtzariaAshurit-Regular.otf', 'OtzariaAshurit-Bold.otf']);
    await loadFamily(ashuritNikudFamily,
        ['OtzariaAshuritNikud-Regular.otf', 'OtzariaAshuritNikud-Bold.otf']);
  });

  test('המנוע מודד כל גליף כפי שהגופן מצהיר', () {
    expect(expectedWidths.keys, containsAll([ashuritFamily, ashuritNikudFamily]));
    expectedWidths.forEach((family, widths) {
      expect(widths, isNotEmpty, reason: family);
      widths.forEach((code, expected) {
        final text = String.fromCharCode(code);
        expect(advance(text, family), closeTo(expected, 1.0),
            reason: '$family U+${code.toRadixString(16).toUpperCase()}');
      });
    });
  });

  test('שתי המשפחות תואמות מטרית', () {
    expectedWidths[ashuritFamily]!.keys.forEach((code) {
      final text = String.fromCharCode(code);
      expect(advance(text, ashuritNikudFamily),
          closeTo(advance(text, ashuritFamily), 0.5),
          reason: 'U+${code.toRadixString(16).toUpperCase()}');
    });
  });

  test('הבולד אינו מזיז אף שורה', () {
    for (final family in [ashuritFamily, ashuritNikudFamily]) {
      for (final text in ['א', 'בראשית ברא אלהים', '']) {
        expect(advance(text, family, weight: FontWeight.bold),
            closeTo(advance(text, family), 0.5), reason: '$family $text');
      }
    }
  });

  test('ל\' חורגת מן השורה אך אינה נחתכת', () {
    final painter = TextPainter(
      text: const TextSpan(text: 'ל', style: TextStyle(fontFamily: ashuritFamily, fontSize: kEm)),
      textDirection: TextDirection.rtl,
    )..layout();
    // הגובה שהמנוע מקצה נשען על hhea; המתאר עולה מעליו, וזה מכוון.
    expect(painter.height, greaterThan(kEm));
  });
}
