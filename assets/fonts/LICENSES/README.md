# Font licences

All fonts in `assets/fonts/` are licensed under the SIL Open Font License 1.1 (OFL). The OFL allows use in
commercial videos and redistribution of the font files with this repo, as long as each licence text travels with
the fonts and the fonts are not sold on their own.

| Font file(s) | Family | Licence text | Source (downloaded 2026-11-18) |
|---|---|---|---|
| Poppins-Medium.ttf, Poppins-SemiBold.ttf, Poppins-Bold.ttf, Poppins-ExtraBold.ttf | Poppins (Indian Type Foundry) | [OFL-Poppins.txt](OFL-Poppins.txt) | https://github.com/google/fonts/tree/main/ofl/poppins |
| CormorantGaramond.ttf (variable) | Cormorant Garamond (Christian Thalmann) | [OFL-CormorantGaramond.txt](OFL-CormorantGaramond.txt) | https://github.com/google/fonts/tree/main/ofl/cormorantgaramond |
| NotoSansDevanagari-Medium.ttf, NotoSansDevanagari-SemiBold.ttf, NotoSansDevanagari-Bold.ttf, NotoSansDevanagari-ExtraBold.ttf | Noto Sans Devanagari (Noto Project Authors) | [OFL-NotoSansDevanagari.txt](OFL-NotoSansDevanagari.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansDevanagari/hinted/ttf (upstream https://github.com/notofonts/devanagari) |
| NotoSansTamil-Medium.ttf, NotoSansTamil-SemiBold.ttf, NotoSansTamil-Bold.ttf, NotoSansTamil-ExtraBold.ttf | Noto Sans Tamil (Noto Project Authors) | [OFL-NotoSansTamil.txt](OFL-NotoSansTamil.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansTamil/hinted/ttf (upstream https://github.com/notofonts/tamil) |
| NotoSansTelugu-Medium.ttf, NotoSansTelugu-SemiBold.ttf, NotoSansTelugu-Bold.ttf, NotoSansTelugu-ExtraBold.ttf | Noto Sans Telugu (Noto Project Authors) | [OFL-NotoSansTelugu.txt](OFL-NotoSansTelugu.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansTelugu/hinted/ttf (upstream https://github.com/notofonts/telugu) |
| NotoSansKannada-Medium.ttf, NotoSansKannada-SemiBold.ttf, NotoSansKannada-Bold.ttf, NotoSansKannada-ExtraBold.ttf | Noto Sans Kannada (Noto Project Authors) | [OFL-NotoSansKannada.txt](OFL-NotoSansKannada.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansKannada/hinted/ttf (upstream https://github.com/notofonts/kannada) |
| NotoSansMalayalam-Medium.ttf, NotoSansMalayalam-SemiBold.ttf, NotoSansMalayalam-Bold.ttf, NotoSansMalayalam-ExtraBold.ttf | Noto Sans Malayalam (Noto Project Authors) | [OFL-NotoSansMalayalam.txt](OFL-NotoSansMalayalam.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansMalayalam/hinted/ttf (upstream https://github.com/notofonts/malayalam) |
| NotoSansBengali-Medium.ttf, NotoSansBengali-SemiBold.ttf, NotoSansBengali-Bold.ttf, NotoSansBengali-ExtraBold.ttf | Noto Sans Bengali (Noto Project Authors) | [OFL-NotoSansBengali.txt](OFL-NotoSansBengali.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansBengali/hinted/ttf (upstream https://github.com/notofonts/bengali) |
| NotoSansGujarati-Medium.ttf, NotoSansGujarati-SemiBold.ttf, NotoSansGujarati-Bold.ttf, NotoSansGujarati-ExtraBold.ttf | Noto Sans Gujarati (Noto Project Authors) | [OFL-NotoSansGujarati.txt](OFL-NotoSansGujarati.txt) | https://github.com/notofonts/notofonts.github.io/tree/main/fonts/NotoSansGujarati/hinted/ttf (upstream https://github.com/notofonts/gujarati) |

Adding a font: OFL or Apache-2.0 only, copy its licence file here as `<LICENCE>-<Family>.txt`, add a row above,
and add the file name to `FONTS` in `setup/doctor.py`. Never commit a client's paid brand font: keep it in the
client's `Brand/` folder.
