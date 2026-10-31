"""
about.py
Kotodama → About Kotodama…: the version, licence and every data source's
credit (owner 2026-10-28). JMdict's licence asks apps to acknowledge it "on
a separate screen reachable from a menu", not only in the documentation, so
this is the add-on's credits screen. Stays English, like Settings.
Keep it in step with the README's "Data sources & credits".
"""

import json
import os

from aqt.qt import *
from aqt import mw

_HERE = os.path.dirname(os.path.abspath(__file__))

CREDITS = """
<h3 style="margin-bottom:2px;">Word lists and dictionaries</h3>
<ul style="margin-top:0;">
<li><b>JLPT word, kanji and grammar lists:</b> <a href="https://github.com/evanclan/OpenJLPT">OpenJLPT</a>
 (CC BY-SA 4.0), with levels from Jonathan Waller's
 <a href="https://web.archive.org/web/20260406082505/http://www.tanos.co.uk/jlpt/">JLPT Resources</a> (CC BY).</li>
<li><b>Dictionary data:</b> this add-on uses the
 <a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project">JMdict</a> and
 <a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project">KANJIDIC2</a> dictionary files.
 These files are the property of the
 <a href="https://www.edrdg.org/">Electronic Dictionary Research and Development Group</a>,
 and are used in conformance with the Group's <a href="https://www.edrdg.org/edrdg/licence.html">licence</a>
 (CC BY-SA 4.0).</li>
<li><b>Meanings on hover:</b> <a href="https://jitendex.org/">Jitendex</a> by Stephen Kraus (CC BY-SA 4.0),
 based on JMdict.</li>
<li><b>Extra JLPT words:</b> words on Waller's lists that OpenJLPT omits, via
 <a href="https://github.com/stephenmk/yomitan-jlpt-vocab">yomitan-jlpt-vocab</a> (CC BY-SA 4.0).</li>
<li><b>Community additions:</b> words from
 <a href="https://github.com/jamsinclair/open-anki-jlpt-decks">open-anki-jlpt-decks</a>
 (© 2020 Jamie Sinclair) and <a href="https://github.com/elzup/jlpt-word-list">jlpt-word-list</a>
 (© 2020 Jamie Sinclair, © 2020 elzup), MIT License: see THIRD_PARTY_NOTICES.txt.</li>
</ul>
<h3 style="margin-bottom:2px;">Frequency data</h3>
<ul style="margin-top:0;">
<li><b>Written Japanese:</b> BCCWJ short- and long-unit word frequency lists v1.0,
 <a href="https://clrd.ninjal.ac.jp/bccwj/en/freq-list.html">National Institute for Japanese Language
 and Linguistics (NINJAL)</a> (CC BY-NC-ND 3.0).</li>
<li><b>Everyday speech:</b> the Corpus of Everyday Japanese Conversation (CEJC) short-unit vocabulary
 table ver202209, <a href="https://www2.ninjal.ac.jp/conversation/cejc.html">NINJAL</a>
 (CC BY-NC-ND 3.0).</li>
</ul>
<h3 style="margin-bottom:2px;">Corpus references</h3>
<ul style="margin-top:0;">
<li>Maekawa, K., Yamazaki, M., Ogiso, T., Maruyama, T., Ogura, H., Kashino, W., Koiso, H., Yamaguchi, M.,
 Tanaka, M., &amp; Den, Y. (2014). Balanced corpus of contemporary written Japanese.
 <i>Language Resources and Evaluation</i>, 48(2), 345–371.
 <a href="https://doi.org/10.1007/s10579-013-9261-0">doi:10.1007/s10579-013-9261-0</a></li>
<li>Koiso, H., Amatani, H., Den, Y., Iseki, Y., Ishimoto, Y., Kashino, W., Kawabata, Y., Nishikawa, K.,
 Tanaka, Y., Watanabe, Y., &amp; Usuda, Y. (2022). Design and Evaluation of the Corpus of Everyday
 Japanese Conversation. <i>Proceedings of LREC 2022</i>, 5587–5594.</li>
<li>小磯花絵・天谷晴香・居關友里子・臼田泰如・柏野和佳子・川端良子・田中弥生・伝康晴・西川賢哉・渡邊友香 (2023)
 「『日本語日常会話コーパス』設計と構築」『国立国語研究所論集』24, 153–168.</li>
</ul>
<p>The derived word, kanji, grammar and meaning files are shared under CC BY-SA 4.0; the frequency
files keep NINJAL's CC BY-NC-ND 3.0 terms.</p>
"""


def _version() -> str:
    try:
        with open(os.path.join(_HERE, "manifest.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "")
    except Exception:
        return ""


def show_about(parent=None):
    dlg = QDialog(parent or mw)
    dlg.setWindowTitle("About Kotodama")
    dlg.setMinimumWidth(560)
    v = QVBoxLayout(dlg)
    head = QLabel(f"<b style='font-size:16px;'>Kotodama 言霊</b>&nbsp; JLPT Progress &amp; Rank Tracker"
                  f"&nbsp; <span style='color:gray;'>v{_version()}</span><br>"
                  "By BenAstromo · code licensed under the "
                  "<a href='https://www.gnu.org/licenses/agpl-3.0.html'>GNU AGPL v3 or later</a>. "
                  "Free, with no affiliation to the JLPT or its organisers.")
    head.setWordWrap(True)
    head.setOpenExternalLinks(True)
    v.addWidget(head)
    body = QTextBrowser()
    body.setOpenExternalLinks(True)
    body.setHtml(CREDITS)
    body.setMinimumHeight(330)
    v.addWidget(body)
    close = QPushButton("Close")
    close.clicked.connect(dlg.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(close)
    v.addLayout(row)
    dlg.exec()
