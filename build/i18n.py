# -*- coding: utf-8 -*-
"""LV -> EN string table for the AUGUSTS page.

English is the site's main language (`site/index.html`); Latvian is the second
variant (`site/lv.html`). The Latvian template stays the source of truth because
the copy is the salon's own wording, and the English page is generated from it —
so all the non-text bytes (SVG, data-* beat timings, srcset, CSS classes) are
byte-identical between the two and can only ever drift on purpose.

Two rules make this reliable, both learned the hard way:

  * Pairs are applied LONGEST SOURCE FIRST. Otherwise a short fragment
    ("Griezums") is replaced inside a longer phrase that contains it
    ("Matu griezums"), leaving half-translated text behind.
  * Sources are ANCHORED with the surrounding markup (`>Cenrādis</a>` rather
    than `Cenrādis`) wherever the same word appears in two roles — nav link and
    section heading, form label and <option> value. Where a phrase legitimately
    occurs more than once in the same role, the anchor is deliberately loose so
    `str.replace` hits every instance.

Latvian words that are ALLOWED to survive on the English page: personal names,
`Rīga` inside the structured data, the footer's own language link, and the
`<option value="...">` service names, which stay Latvian on purpose so the
salon's form inbox reads one consistent set of names in both languages.
"""

# Words that may carry Latvian diacritics on the English page. Everything else
# with a macron/caron is a missed string — assemble.py fails the build on it.
EN_DIACRITIC_ALLOWLIST = {
    "Kristīne", "Kristīnes",   # person's name
    "Rīga",                    # JSON-LD addressLocality stays local-form
    "Latviešu", "valodā",      # the footer link *to* the Latvian page
}

# The header and the footer are one partial each, shared by the front page and
# the review page — so their strings must be shared too, or the second page keeps
# a Latvian nav on the English site. That is exactly what happened the first time
# these lived only in PAIRS.
CHROME_PAIRS = [
    ('aria-label="AUGUSTS /08/ — sākums"', 'aria-label="AUGUSTS /08/ — home"'),
    ('aria-label="Galvenā navigācija"', 'aria-label="Main navigation"'),
    ('#pakalpojumi">Pakalpojumi</a>', '#pakalpojumi">Services</a>'),
    ('#darbi">Darbi</a>', '#darbi">Work</a>'),
    ('{{REVIEWS}}">Atsauksmes</a>', '{{REVIEWS}}">Reviews</a>'),
    ('#komanda">Komanda</a>', '#komanda">Team</a>'),
    ('#par-mums">Par mums</a>', '#par-mums">About</a>'),
    ('#kontakti">Kontakti</a>', '#kontakti">Contact</a>'),
    ('#pieraksts">Rezervēt</a>', '#pieraksts">Book</a>'),
    ("AUGUSTS /08/ · Miera iela 19, Rīga · Visas tiesības aizsargātas",
     "AUGUSTS /08/ · Miera iela 19, Riga · All rights reserved"),
    ('<a class="ftr__link" href="{{REVIEWS}}">Atsauksmes</a>',
     '<a class="ftr__link" href="{{REVIEWS}}">Reviews</a>'),
    ('aria-label="Zvanīt"', 'aria-label="Call"'),
]

PAIRS = CHROME_PAIRS + [
    # ------------------------------------------------------------------ <head>
    ("<title>AUGUSTS /08/ — frizierdarbnīca Miera ielā 19, Rīgā | Online pieraksts</title>",
     "<title>AUGUSTS /08/ — hair studio on Miera iela 19, Riga | Book online</title>"),
    ("AUGUSTS /08/ — maza frizierdarbnīca Miera ielā 19, Rīgā. Griezumi, krāsošana, balināšana (Air touch, Balayage), tonēšana un bārdas formēšana. Cenrādis un online pieraksts.",
     "AUGUSTS /08/ — a small hair studio at Miera iela 19, Riga. Cuts, colour, lightening (Air touch, Balayage), toning and beard shaping. Price list and online booking."),
    ('content="AUGUSTS /08/ — frizierdarbnīca Miera ielā 19, Rīgā">',
     'content="AUGUSTS /08/ — hair studio on Miera iela 19, Riga">'),
    ("Ienāc kā svešinieks, aizej kā draugs. Griezumi, krāsošana un balināšana Miera ielā. Rezervē laiku online.",
     "Come in a stranger, leave a friend. Cuts, colour and lightening on Miera iela. Book your time online."),

    # JSON-LD
    ('"alternateName": "Augusts frizierdarbnīca"',
     '"alternateName": "Augusts hair studio"'),
    ('"description": "Frizierdarbnīca Miera ielā 19, Rīgā. Griezumi, krāsošana, balināšana, tonēšana, bārdas formēšana."',
     '"description": "Hair studio at Miera iela 19, Riga. Cuts, colour, lightening, toning and beard shaping."'),
    ('"jobTitle": "Meistare, dibinātāja"', '"jobTitle": "Stylist, founder"'),
    ('"jobTitle": "Jaunā meistare"', '"jobTitle": "Junior stylist"'),

    # ------------------------------------------------------------- header / nav
    (">Pāriet uz pakalpojumiem</a>", ">Skip to the services</a>"),

    # ------------------------------------------------------------------ the film
    ('aria-label="AUGUSTS — ievads"', 'aria-label="AUGUSTS — intro"'),
    ('alt="AUGUSTS zīmols — fotogrāfija Latvijas mežā"',
     'alt="The AUGUSTS mark — photographed in a Latvian forest"'),
    ("<figcaption>Mežs · Latvija</figcaption>", "<figcaption>Forest · Latvia</figcaption>"),
    ('alt="Sarkanmataina meitene ar pīlādžu ogām matos"',
     'alt="Red-haired woman with rowan berries in her hair"'),
    ("<figcaption>Pīlādža tonis</figcaption>", "<figcaption>Rowan tone</figcaption>"),
    ('alt="Krāsainu matu šķipsnu palete darba procesā"',
     'alt="A fan of hair-colour swatches mid-appointment"'),
    ("<figcaption>Krāsu palete</figcaption>", "<figcaption>Colour palette</figcaption>"),
    ('alt="Meistars darbā AUGUSTS salonā"', 'alt="A stylist at work in the AUGUSTS studio"'),
    ("<figcaption>Darbnīcā</figcaption>", "<figcaption>In the studio</figcaption>"),
    # this alt is used by both the film plate and the gallery — hit both
    ('alt="Gari viļņoti mati pēc krāsošanas"', 'alt="Long wavy hair after colouring"'),
    ("<figcaption>Aizej kā draugs</figcaption>", "<figcaption>Leave a friend</figcaption>"),

    ('<span class="sr-only">AUGUSTS /08/ — frizierdarbnīca</span>',
     '<span class="sr-only">AUGUSTS /08/ — hair studio</span>'),
    (">Miera iela 19, Rīga</p>", ">Miera iela 19, Riga</p>"),

    (">01 · Mežs</p>", ">01 · Forest</p>"),
    ("<h2>Krāsu mēs<br><em>neizvēlamies no kataloga.</em></h2>",
     "<h2>We don't pick colour<br><em>out of a catalogue.</em></h2>"),
    ("""<p>Rudens pīlādzis, bērza miza, sūnas tonis. Latvijas mežā ir viss, ko
           vajag, lai atrastu toni, kas tev tiešām piestāv.</p>""",
     """<p>Autumn rowan, birch bark, the tone of moss. A Latvian forest holds
           everything you need to find a colour that actually suits you.</p>"""),

    (">02 · Krāsa</p>", ">02 · Colour</p>"),
    ("<h2>Balināšana.<br>Tonēšana.<br><em>Air touch.</em></h2>",
     "<h2>Lightening.<br>Toning.<br><em>Air touch.</em></h2>"),
    ("""<p>Strādājam ar dažādiem sastāviem un piemeklējam to, kas matam nodara
           vismazāko kaitējumu. Pēc balināšanas vienmēr tonējam.</p>""",
     """<p>We work with several formulas and pick the one that does your hair the
           least harm. After lightening we always tone.</p>"""),

    (">03 · Adrese</p>", ">03 · Address</p>"),
    ("""<p style="margin-inline:auto">Mazs salons ar lielu logu.
           Nāc iekšā — kafija jau ir uzlikta.</p>""",
     """<p style="margin-inline:auto">A small studio with a big window.
           Come in — the coffee is already on.</p>"""),

    (">04 · Krēsls</p>", ">04 · The chair</p>"),
    ("<h2>Divas stundas,<br><em>tikai tev.</em></h2>",
     "<h2>Two hours,<br><em>just for you.</em></h2>"),
    ("""<p>Strādājam pa vienam klientam. Nesteidzamies, un vispirms izrunājam,
           ko tu tiešām gribi.</p>""",
     """<p>We take one client at a time. No rushing — and we talk through what you
           actually want before we start.</p>"""),

    ("<h2>Ienāc kā svešinieks,<br><em>aizej kā draugs.</em></h2>",
     "<h2>Come in a stranger,<br><em>leave a friend.</em></h2>"),

    ('data-i="0">Mežs</span>', 'data-i="0">Forest</span>'),
    ("<i></i> Ritini</div>", "<i></i> Scroll</div>"),

    # ---------------------------------------------------------------- services
    (">Pakalpojumi</p>", ">Services</p>"),
    ('<h2 class="h-lg">Ko mēs darām</h2>', '<h2 class="h-lg">What we do</h2>'),
    ("Sešas lietas, pēc kurām pie mums nāk visbiežāk. Pilns cenrādis ir zemāk.",
     "The six things people come to us for most. The full price list is below."),
    (">Pilns cenrādis</p>", ">The full price list</p>"),
    ('<h2 class="h-md">Visi pakalpojumi un cenas</h2>',
     '<h2 class="h-md">Every service and what it costs</h2>'),
    ("""Cena atkarīga no matu garuma, biezuma un darba apjoma. Precīzu cenu
        pasakām konsultācijā, pirms sākam darbu.""",
     """The price depends on hair length, thickness and how much work it takes.
        We tell you the exact price in the consultation, before we start."""),

    # the six service cards
    ('<span class="svcard__name">Griezums</span>', '<span class="svcard__name">Haircut</span>'),
    ("Sievietēm, vīriešiem un bērniem. Piemeklējam tavam matu tipam, sejas formai un ikdienai.",
     "For women, men and children. Matched to your hair type, your face and your everyday life."),
    ('<span class="svcard__name">Matu krāsošana</span>', '<span class="svcard__name">Hair colouring</span>'),
    ("Toni meklējam dabā, ne katalogā. Ir arī vīriešu krāsas sirmajiem matiem.",
     "We look for the tone in nature, not in a catalogue. There is a men's colour for grey hair too."),
    ('<span class="svcard__name">Balināšana</span>', '<span class="svcard__name">Lightening</span>'),
    ("Air touch, Balayage, baby highlights. Pēc balināšanas vienmēr tonējam.",
     "Air touch, Balayage, baby highlights. After lightening we always tone."),
    ('<span class="svcard__name">Spilgtie toņi</span>', '<span class="svcard__name">Bright shades</span>'),
    ("Košas krāsas no Amerikas, noturīgas. Lai tonis būtu spilgts, matus vispirms izbalinām.",
     "Vivid colours from the States, and they hold. For a really bright result the hair is lightened first."),
    ('<span class="svcard__name">Veidošana</span>', '<span class="svcard__name">Styling</span>'),
    ("Ikdienai un svinīgiem notikumiem — vakara frizūras un sarežģītāki veidojumi.",
     "For an ordinary day and for a celebration — evening hair and more elaborate work."),
    ('<span class="svcard__name">Bārdas formēšana</span>', '<span class="svcard__name">Beard shaping</span>'),
    ("Formējam bārdu atsevišķi vai kopā ar griezumu, 30 minūtēs.",
     "On its own or alongside a haircut, in half an hour."),
    ('alt="Gari viļņoti mati pēc balināšanas un tonēšanas"',
     'alt="Long wavy hair after lightening and toning"'),
    ('alt="Īss griezums, skats no muguras"', 'alt="A short cut seen from behind"'),
    ('alt="Vīriešu griezums un formēta bārda"', "alt=\"A men's cut and a shaped beard\""),
    ('aria-label="Pakalpojumu grupas"', 'aria-label="Service groups"'),
    ('data-panel="women">Sievietēm</button>', 'data-panel="women">Women</button>'),
    ('data-panel="men">Vīriešiem</button>', 'data-panel="men">Men</button>'),
    ('data-panel="kids">Bērniem</button>', 'data-panel="kids">Kids</button>'),

    # service names (h3) — `>…</h3>` anchored, replace-all where a name repeats
    (">Griezums</h3>", ">Haircut</h3>"),
    (">Matu krāsošana</h3>", ">Hair colouring</h3>"),
    (">Matu balināšana dažādās tehnikās</h3>", ">Lightening in various techniques</h3>"),
    (">Krāsas labošana / izņemšana</h3>", ">Colour correction / removal</h3>"),
    (">Matu balināšana</h3>", ">Hair lightening</h3>"),
    (">Tonēšana</h3>", ">Toning</h3>"),
    (">Veidošana</h3>", ">Styling</h3>"),
    (">Matu ķīmiskā taisnošana</h3>", ">Chemical hair straightening</h3>"),
    (">Krāsošana spilgtos toņos</h3>", ">Colouring in bright shades</h3>"),
    (">Frizūras veidošana īpašiem gadījumiem</h3>", ">Styling for special occasions</h3>"),
    (">Krāsošana ar vīriešu krāsām</h3>", ">Colouring with men's colour</h3>"),
    (">Balināšana + tonēšana</h3>", ">Lightening + toning</h3>"),
    (">Bārdas formēšana</h3>", ">Beard shaping</h3>"),
    (">Matu griezums</h3>", ">Haircut</h3>"),

    # durations — anchored on the class so a bare "1 h" can't be hit elsewhere
    ('dur">1 h 30 min</span>', 'dur">1 hr 30 min</span>'),
    ('dur">1 h</span>', 'dur">1 hr</span>'),
    ('dur">2 h</span>', 'dur">2 hrs</span>'),
    ('dur">3 h</span>', 'dur">3 hrs</span>'),

    # service descriptions
    ("""Air touch, Balayage, baby highlights. Pirms pierakstīšanās vēlams sagatavot
            bildi ar vēlamo rezultātu un savu esošo matu bildi — tad izrunāsim un
            piemērosim tehniku, kādā strādāt.""",
     """Air touch, Balayage, baby highlights. Before booking, bring a photo of the
            result you want and one of your hair as it is now — then we'll talk it
            through and choose the technique to work in."""),
    ("""Izmantojam dažādus ķīmiskos sastāvus, piemeklējam piemērotāko, lai maksimāli
            saudzīgi tiktu vaļā no nevēlamā mata toņa.""",
     """We use several chemical formulas and pick the most suitable one, to get rid
            of an unwanted tone as gently as possible."""),
    ("Pēc matu balināšanas vienmēr tos tonējam, lai sasniegtu vēlamo toni.",
     "After lightening we always tone the hair to reach the shade you want."),
    ("""Procedūra tiem, kuri vēlas taisnus, gludus matus. Atšķirībā no keratīna
            taisnošanas tā jāveic daudz retāk — taisni mati paliek, kamēr ataug.
            Ilgums atkarīgs no matu garuma un biezuma, apmēram 2–4 h.""",
     """For anyone who wants straight, smooth hair. Unlike keratin straightening it
            needs repeating far less often — the hair stays straight until it grows
            out. Takes roughly 2–4 h depending on length and thickness."""),
    ("""Strādājam ar košām krāsām no Amerikas, kuras ir diezgan noturīgas. Lai panāktu
            maksimāli spilgtu rezultātu, pirms tam matus nepieciešams izbalināt.""",
     """We work with vivid colours from the States, which hold fairly well. To get a
            really bright result the hair has to be lightened first."""),
    ("Vakara frizūras un sarežģītāki veidojumi svinīgiem notikumiem.",
     "Evening hair and more elaborate work for celebrations."),
    ("""Ar šo krāsu varam nokrāsot sirmos matus — mēneša laikā tā izmazgājas un
            neveido ataugušu sakņu līniju. Krāsu piemeklējam mata dabīgajā tonī.""",
     """This colour covers grey hair — it washes out within a month and leaves no
            regrowth line. We match it to your natural tone."""),
    ("""Ir iespēja krāsot ar krāsainām maskām, kuras izmazgājas, kā arī ar košām
            noturīgām krāsām. Cena atkarīga no krāsošanas daudzuma.""",
     """We can colour with washable colour masks, or with vivid long-lasting
            colours. The price depends on how much colouring is involved."""),

    # per-service booking links (data-svc drives the modal's title)
    ('data-svc="Griezums ar Adeli (−50%)"', 'data-svc="Haircut with Adele (−50%)"'),
    ('data-svc="Matu balināšana dažādās tehnikās"', 'data-svc="Lightening in various techniques"'),
    ('data-svc="Frizūras veidošana īpašiem gadījumiem"', 'data-svc="Styling for special occasions"'),
    ('data-svc="Krāsas labošana / izņemšana"', 'data-svc="Colour correction / removal"'),
    ('data-svc="Krāsošana ar vīriešu krāsām"', 'data-svc="Colouring with men\'s colour"'),
    ('data-svc="Matu ķīmiskā taisnošana"', 'data-svc="Chemical hair straightening"'),
    ('data-svc="Krāsošana spilgtos toņos"', 'data-svc="Colouring in bright shades"'),
    ('data-svc="Matu krāsošana bērnam"', 'data-svc="Hair colouring for a child"'),
    ('data-svc="Matu griezums bērnam"', 'data-svc="Haircut for a child"'),
    ('data-svc="Balināšana + tonēšana"', 'data-svc="Lightening + toning"'),
    ('data-svc="Vīriešu griezums"', 'data-svc="Men\'s haircut"'),
    ('data-svc="Bārdas formēšana"', 'data-svc="Beard shaping"'),
    ('data-svc="Matu balināšana"', 'data-svc="Hair lightening"'),
    ('data-svc="Matu krāsošana"', 'data-svc="Hair colouring"'),
    ('data-svc="Kristīne Kazoka"', 'data-svc="Kristīne Kazoka"'),
    ('data-svc="Veidošana"', 'data-svc="Styling"'),
    ('data-svc="Tonēšana"', 'data-svc="Toning"'),
    ('data-svc="Griezums"', 'data-svc="Haircut"'),

    (">Rezervēt<span aria-hidden=\"true\">→</span></a>", ">Book<span aria-hidden=\"true\">→</span></a>"),
    (">Rezervēt laiku</a>", ">Book a time</a>"),

    ("""Cenas ar “/h” ir stundas likme. Norādītais ilgums ir laiks, ko rezervējam kalendārā.""",
     """Prices marked “/h” are hourly rates. The time shown is what we block out in the calendar."""),
    (">Pakalpojumi bērniem līdz 10 gadu vecumam.</p>",
     ">Services for children up to 10 years old.</p>"),

    # ----------------------------------------------------------------- gallery
    (">No darbnīcas</p>", ">From the studio</p>"),
    ('<h2 class="h-lg">Mūsu darbi</h2>', '<h2 class="h-lg">Our work</h2>'),
    ('alt="Zili krāsoti īsie mati"', 'alt="Short hair coloured blue"'),
    ('alt="Īss griezums, skats no muguras, melnbalta fotogrāfija"',
     'alt="A short cut seen from behind, in black and white"'),
    ('alt="Dabīgas cirtas zaļumā"', 'alt="Natural curls out in the green"'),
    ('alt="Vīriešu griezums, melnbalta studijas fotogrāfija"',
     'alt="A men\'s cut, black-and-white studio photograph"'),
    ('alt="Studijas portrets ar veidotu frizūru"', 'alt="Studio portrait with styled hair"'),
    ('alt="Kolāža ar īsu bobu"', 'alt="Collage of a short bob"'),
    ('alt="AUGUSTS zīmols — fotogrāfija mežā"', 'alt="The AUGUSTS mark — photographed in the forest"'),

    # ------------------------------------------------------------------- about
    ('alt="AUGUSTS salona ikdiena — meistars pie darba"',
     'alt="An ordinary day at AUGUSTS — a stylist at work"'),
    (">Par mums</p>", ">About us</p>"),
    ("""“Vieta, kurā ienāci kā svešinieks<br>un aizgāji <span>kā draugs.</span>”""",
     """“A place you walked into a stranger<br>and left <span>as a friend.</span>”"""),
    ("""AUGUSTS ir neliela frizierdarbnīca Miera ielā. Strādājam nesteidzīgi un
        pa vienam klientam — lai pietiek laika izrunāt, ko tu tiešām gribi.""",
     """AUGUSTS is a small hair studio on Miera iela. We work slowly and one client
        at a time — so there is time to talk through what you actually want."""),
    ("<b>Bez šablona</b>", "<b>No template</b>"),
    ("<p>Griezumu un toni piemeklējam tavam matu tipam, sejas formai un ikdienai — ne pēc kataloga.</p>",
     "<p>We match the cut and the tone to your hair type, your face and your everyday life — not to a catalogue.</p>"),
    ("<b>Saudzīgi pret matiem</b>", "<b>Gentle on the hair</b>"),
    ("<p>Balināšanai un krāsas izņemšanai piemeklējam sastāvu, kas matam nodara vismazāko kaitējumu.</p>",
     "<p>For lightening and colour removal we pick the formula that does your hair the least harm.</p>"),
    ("<b>Silta vieta</b>", "<b>A warm room</b>"),
    ("<p>Mazs salons Miera ielā, kur nesteidzas, kur tevi atceras un kur var vienkārši parunāt.</p>",
     "<p>A small studio on Miera iela where nobody rushes, where you are remembered, and where you can simply talk.</p>"),

    # -------------------------------------------------------------------- team
    (">Komanda</p>", ">Team</p>"),
    ('<h2 class="h-lg">Kas tevi sagaidīs</h2>', '<h2 class="h-lg">Who will look after you</h2>'),
    ("""Strādājam pa vienam klientam, tāpēc zini jau iepriekš, kura rokās
        būsi.""",
     """We take one client at a time, so you know whose hands you will be in
        before you arrive."""),
    ('alt="Kristīne Kazoka — meistare un darbnīcas saimniece"',
     'alt="Kristīne Kazoka — stylist and owner of the studio"'),
    ('alt="Adele Axelle — jaunā meistare"', 'alt="Adele Axelle — junior stylist"'),
    (">Meistare · darbnīcas saimniece</p>", ">Stylist · owner of the studio</p>"),
    ("""Griezumi, krāsošana un balināšana. Vispirms izrunājam, ko tu tiešām
            gribi, un tikai tad sākam griezt.""",
     """Cuts, colour and lightening. First we talk through what you actually
            want, and only then start cutting."""),
    (">Rezervēt pie Kristīnes<span", ">Book with Kristīne<span"),
    (">Jaunā meistare</p>", ">Junior stylist</p>"),
    ("""Šobrīd mācās un pilnveido prasmes, tāpēc griezums pie Adeles ir ar
            50% atlaidi.""",
     """Currently learning and building her skills, which is why a haircut with
            Adele comes with 50% off."""),
    (">Latviešu — mācās · angļu un krievu — brīvi</p>",
     ">Latvian — learning · English and Russian — fluent</p>"),
    (">Rezervēt pie Adeles<span", ">Book with Adele<span"),
    (">Meistare</p>", ">Stylist</p>"),
    ('alt="Maija Goldberga — meistare"', 'alt="Maija Goldberga — stylist"'),
    ("""Griezumi, krāsošana un veidošana. Tāpat kā pārējās — pa vienam
            klientam un bez steigas. Griezums pie Maijas šobrīd ir ar 50%
            atlaidi.""",
     """Cuts, colour and styling. Same as the rest of us — one client at a
            time, and no rushing. A haircut with Maija currently comes with 50%
            off."""),
    (">Latviešu un angļu — brīvi · krievu — nedaudz</p>",
     ">Latvian and English — fluent · Russian — a little</p>"),
    ('data-svc="Griezums ar Maiju (−50%)"', 'data-svc="Haircut with Maija (−50%)"'),
    (">Rezervēt pie Maijas<span", ">Book with Maija<span"),

    # ----------------------------------------------------------------- booking
    (">Online pieraksts</p>", ">Online booking</p>"),   # section eyebrow + modal title
    ('<h2 class="h-lg">Rezervē laiku</h2>', '<h2 class="h-lg">Book your time</h2>'),
    ("""Izvēlies sev ērtu dienu un laiku. Apstiprinājumu saņemsi e-pastā uzreiz
        pēc pieraksta.""",
     """Pick a day and a time that suit you. The confirmation lands in your inbox
        straight away."""),
    ("""Piezīmju laukā uzraksti, kuru pakalpojumu vēlies — tam vajadzīgo laiku
        ieplānojam mēs.""",
     """Write which service you would like in the notes field — blocking out the
        time it needs is on us."""),
    ('<p class="book__fallback">Kalendārs neatveras? <a',
     '<p class="book__fallback">Calendar not opening? <a'),
    (">Atvērt pierakstu jaunā logā</a>", ">Open the booking in a new window</a>"),
    ('title="AUGUSTS online pieraksta kalendārs"', 'title="AUGUSTS online booking calendar"'),

    # ----------------------------------------------------------------- contact
    (">Kontakti</p>", ">Contact</p>"),
    ('<h2 class="h-lg" style="margin-bottom:2rem">Kā mūs atrast</h2>',
     '<h2 class="h-lg" style="margin-bottom:2rem">How to find us</h2>'),
    ("<b>Adrese</b>", "<b>Address</b>"),
    (">Miera iela 19, Rīga, LV-1001</a>", ">Miera iela 19, Riga, LV-1001</a>"),
    ("<b>Telefons</b>", "<b>Phone</b>"),
    ("<b>E-pasts</b>", "<b>Email</b>"),
    ("<b>Darba laiks</b>", "<b>Opening hours</b>"),
    ("Pirmdiena–Piektdiena <span>10:00–20:00</span><br>Sestdiena, Svētdiena <span>slēgts</span>",
     "Monday–Friday <span>10:00–20:00</span><br>Saturday, Sunday <span>closed</span>"),
    ('aria-label="Atvērt AUGUSTS atrašanās vietu Google Maps"',
     'aria-label="Open the AUGUSTS location in Google Maps"'),
    ('alt="Karte — Miera iela 19, Rīga"', 'alt="Map — Miera iela 19, Riga"'),

    (">Neatradi brīvu laiku?</p>", ">No time that works?</p>"),
    ('style="margin-bottom:.6rem">Atstāj ziņu — atzvanīsim</h2>',
     'style="margin-bottom:.6rem">Leave a message — we will call you back</h2>'),
    ("""Ja kalendārā nav piemērota laika vai vēl nezini, kurš pakalpojums tev vajadzīgs —
        uzraksti, un sazināsimies.""",
     """If nothing in the calendar suits, or you are not sure yet which service you
        need — write to us and we will be in touch."""),
    ("<label>Neaizpildi šo lauku: ", "<label>Do not fill in this field: "),
    ('for="f-name">Vārds</label>', 'for="f-name">Name</label>'),
    ('placeholder="Tavs vārds"', 'placeholder="Your name"'),
    ('for="f-tel">Telefons</label>', 'for="f-tel">Phone</label>'),
    ('for="f-svc">Pakalpojums</label>', 'for="f-svc">Service</label>'),
    ('for="f-msg">Ziņa</label>', 'for="f-msg">Message</label>'),
    ('placeholder="Kad tev būtu ērti? Ko vēlies izdarīt ar matiem?"',
     'placeholder="When would suit you? What would you like to do with your hair?"'),

    # <option> LABELS translate; value= stays Latvian so the inbox is consistent
    ('value="Griezums">Griezums</option>', 'value="Griezums">Haircut</option>'),
    ('value="Matu krāsošana">Matu krāsošana</option>', 'value="Matu krāsošana">Hair colouring</option>'),
    ('value="Balināšana (Air touch, Balayage)">Balināšana (Air touch, Balayage)</option>',
     'value="Balināšana (Air touch, Balayage)">Lightening (Air touch, Balayage)</option>'),
    ('value="Krāsas labošana / izņemšana">Krāsas labošana / izņemšana</option>',
     'value="Krāsas labošana / izņemšana">Colour correction / removal</option>'),
    ('value="Tonēšana">Tonēšana</option>', 'value="Tonēšana">Toning</option>'),
    ('value="Veidošana / vakara frizūra">Veidošana / vakara frizūra</option>',
     'value="Veidošana / vakara frizūra">Styling / evening hair</option>'),
    ('value="Vīriešu griezums vai bārda">Vīriešu griezums vai bārda</option>',
     'value="Vīriešu griezums vai bārda">Men\'s cut or beard</option>'),
    ('value="Pakalpojums bērnam">Pakalpojums bērnam</option>',
     'value="Pakalpojums bērnam">Something for a child</option>'),
    ('value="Vēl nezinu — vajag padomu">Vēl nezinu — vajag padomu</option>',
     'value="Vēl nezinu — vajag padomu">Not sure yet — I would like advice</option>'),

    ('type="submit">Nosūtīt</button>', 'type="submit">Send</button>'),
    ("""Nosūtot formu, piekrīti, ka sazināmies ar tevi par pierakstu. Datus neizmantojam citiem mērķiem.""",
     """By sending this form you agree that we may contact you about your booking. We do not use your details for anything else."""),

    # ------------------------------------------------------------------ footer

    # ------------------------------------------------------------------- modal
    ('id="modalNewTab" href="#" target="_blank" rel="noopener">Jaunā logā</a>',
     'id="modalNewTab" href="#" target="_blank" rel="noopener">New window</a>'),
    ('aria-label="Aizvērt"', 'aria-label="Close"'),
]

# ---------------------------------------------------------------------------
# The review page's own string table. It is separate from PAIRS because the two
# templates share only the header and the footer, and those live in their own
# partials — a single flat table would have to declare every source found in
# either page, and assemble.py fails a pair whose source is missing.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# The review page's own string table. Separate from PAIRS because the two
# templates share only the header and the footer, and those live in their own
# partials — a single flat table would have to declare every source found in
# either page, and assemble.py fails a pair whose source is missing.
#
# Short, because the page is short: the Google wall's own chrome is translated
# inside build/google_reviews.py (a rendered token cannot be reached by this
# table, since substitution happens after the pairs are applied), and the review
# TEXT is deliberately never translated at all.
# ---------------------------------------------------------------------------
REVIEW_PAIRS = CHROME_PAIRS + [
    ("<title>Atsauksmes — AUGUSTS /08/ frizierdarbnīca, Miera iela 19</title>",
     "<title>Reviews — AUGUSTS /08/ hair studio, Miera iela 19</title>"),
    ("Klientu atsauksmes par AUGUSTS /08/ frizierdarbnīcu Miera ielā 19, Rīgā — 4,9 zvaigznes Google. Izlasi, ko saka klienti, un atstāj savu atsauksmi Google.",
     "Client reviews of AUGUSTS /08/ hair studio at Miera iela 19, Riga — 4.9 stars on Google. Read what clients say, and leave your own review on Google."),
    ('content="Atsauksmes — AUGUSTS /08/">', 'content="Reviews — AUGUSTS /08/">'),
    ("Ko klienti saka par AUGUSTS /08/ — 4,9 no 5 Google atsauksmēs.",
     "What clients say about AUGUSTS /08/ — 4.9 out of 5 across their Google reviews."),
    (">Pāriet uz atsauksmēm</a>", ">Skip to the reviews</a>"),

    (">Atsauksmes</p>", ">Reviews</p>"),
    ('<h1 class="h-lg">Pastāsti, kā gāja</h1>', '<h1 class="h-lg">Tell us how it went</h1>'),
    ("""Mēs strādājam pa vienam klientam un bez steigas, tāpēc katra atsauksme
      mums tiešām kaut ko pasaka. Zemāk ir viss, ko klienti raksta mūsu Google
      profilā. Ja arī tev ir ko teikt — tas aizņem divas minūtes.""",
     """We work one client at a time and without rushing, so a review actually
      tells us something. Below is everything clients have written on our Google
      profile. If you have something to say too — it takes two minutes."""),
]

# ---------------------------------------------------------------------------
# Per-language values for the {{TOKEN}} placeholders in the templates.
#
# Four token groups matter and are easy to get subtly wrong:
#   HOME       "" on the front page, the other page's filename on a sub-page —
#              so `{{HOME}}#kontakti` is an in-page anchor where the section
#              exists and a cross-page link where it does not.
#   HOME_LINK  where the logo goes. On the front page that is the film, not the
#              file, or clicking it reloads the page.
#   REVIEWS    the review page IN THIS LANGUAGE. An English page linking to
#              atsauksmes.html silently drops the visitor into Latvian.
#   LANGPILL   must switch to the SAME page in the other language. Pointing it
#              at index.html from the review page throws away where they were.
# ---------------------------------------------------------------------------
def pill(active, en_href, lv_href):
    """The EN|LV segmented switch. Relative hrefs so it works off disk too."""
    def one(code, href, lang):
        cur = ' aria-current="page"' if code == active else ''
        return f'<a href="{href}" hreflang="{lang}"{cur}>{code}</a>'
    return ('<span class="langpill" role="group" aria-label="Valoda / Language">'
            + one("EN", en_href, "en")
            + one("LV", lv_href, "lv")
            + '</span>')


LANGS = {
    "en": {
        "file":      "index.html",
        "LANG":      "en",
        "LANGCODE":  "EN",
        "OG_LOCALE": "en_US",
        "CANONICAL": "https://augusts08.lv/",
        "TY_PAGE":   "thank-you.html",
        "CHAPTERS":  "Forest|Berries|Colour|Miera 19|Mirror|Friend",
        "LANGPILL":  pill("EN", "index.html", "lv.html"),
        "FTR_LANG":  '<a class="ftr__link" href="lv.html" hreflang="lv">Latviešu valodā</a>',
        "HOME":      "",
        "HOME_LINK": "#film",
        "REVIEWS":   "reviews.html",
        "translate": True,
    },
    "lv": {
        "file":      "lv.html",
        "LANG":      "lv",
        "LANGCODE":  "LV",
        "OG_LOCALE": "lv_LV",
        "CANONICAL": "https://augusts08.lv/lv.html",
        "TY_PAGE":   "paldies.html",
        "CHAPTERS":  "Mežs|Ogas|Krāsa|Miera 19|Spogulis|Draugs",
        "LANGPILL":  pill("LV", "index.html", "lv.html"),
        "FTR_LANG":  '<a class="ftr__link" href="index.html" hreflang="en">In English</a>',
        "HOME":      "",
        "HOME_LINK": "#film",
        "REVIEWS":   "atsauksmes.html",
        "translate": False,
    },
}

REVIEW_LANGS = {
    "en": {
        "file":      "reviews.html",
        "LANG":      "en",
        "OG_LOCALE": "en_US",
        "CANONICAL": "https://augusts08.lv/reviews.html",
        "LANGPILL":  pill("EN", "reviews.html", "atsauksmes.html"),
        "FTR_LANG":  '<a class="ftr__link" href="atsauksmes.html" hreflang="lv">Latviešu valodā</a>',
        "HOME":      "index.html",
        "HOME_LINK": "index.html",
        "REVIEWS":   "reviews.html",
        "translate": True,
    },
    "lv": {
        "file":      "atsauksmes.html",
        "LANG":      "lv",
        "OG_LOCALE": "lv_LV",
        "CANONICAL": "https://augusts08.lv/atsauksmes.html",
        "LANGPILL":  pill("LV", "reviews.html", "atsauksmes.html"),
        "FTR_LANG":  '<a class="ftr__link" href="reviews.html" hreflang="en">In English</a>',
        "HOME":      "lv.html",
        "HOME_LINK": "lv.html",
        "REVIEWS":   "atsauksmes.html",
        "translate": False,
    },
}

# The thank-you page is small enough to keep its own table.
TY_PAIRS = [
    ("<title>Paldies! — AUGUSTS /08/</title>", "<title>Thank you! — AUGUSTS /08/</title>"),
    ("Paldies par ziņu — sazināsimies ar tevi tuvākajā laikā. AUGUSTS /08/ frizierdarbnīca, Miera iela 19, Rīga.",
     "Thanks for your message — we will be in touch shortly. AUGUSTS /08/ hair studio, Miera iela 19, Riga."),
    (">Ziņa nosūtīta</p>", ">Message sent</p>"),
    ('<h1 class="h-lg">Paldies! Sazināsimies ar tevi.</h1>',
     '<h1 class="h-lg">Thank you! We will be in touch.</h1>'),
    ("""Tava ziņa ir saņemta. Atzvanīsim vai uzrakstīsim tuvākajā darba dienā, lai
      saskaņotu tev ērtāko laiku.""",
     """We have your message. We will call or write on the next working day to
      settle on the time that suits you best."""),
    (">Skatīt brīvos laikus</a>", ">See the free times</a>"),
    (">Atpakaļ uz sākumu</a>", ">Back to the start</a>"),
    ("<span>Steidzami? ", "<span>In a hurry? "),
    ('<span class="num">Miera iela 19, Rīga · P–Pk 10:00–20:00</span>',
     '<span class="num">Miera iela 19, Riga · Mon–Fri 10:00–20:00</span>'),
    ('aria-label="AUGUSTS /08/ — sākums"', 'aria-label="AUGUSTS /08/ — home"'),
]


TY_LANGS = {
    "en": {"file": "thank-you.html", "LANG": "en", "HOME": "index.html", "translate": True},
    "lv": {"file": "paldies.html",   "LANG": "lv", "HOME": "lv.html",    "translate": False},
}

