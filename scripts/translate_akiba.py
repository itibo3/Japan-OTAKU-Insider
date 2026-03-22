import json

translations = {
    "cafe-20260318-rss-d65a17": {
        "title": "Dream☆Jumbo☆Girl Vol.4: \"Tens of millions of yen is cheap for my friends!\"",
        "description": "Hiroyuki's manga 'Dream Jumbo Girl' Volume 4 was released on the 17th. A super happy girls' comedy starting from winning the lottery top prize."
    },
    "cafe-20260318-rss-f64450": {
        "title": "Idolatry Vol.3: \"Junna's crazy love destroys the concept of Otaku and Oshi\"",
        "description": "'Idolatry' Volume 3 by Shin Otaka & Homare was released on the 17th. Junna faces new challenges on the 3rd stage Grind Isle. Recommended by voice actress Yu Serizawa."
    },
    "cafe-20260318-rss-e564ce": {
        "title": "Keichi Kiyuna's 'Athena-san Who Demands a Return' Vol.1: 'Runaway Beautiful Girl x Yare-yare Boy!'",
        "description": "Keichi Kiyuna's first manga book 'Mikaeri wo Motomeru Athena-san' Volume 1 was released on the 17th. A youth comedy featuring an incredibly out-of-control beautiful girl and an apathetic boy."
    },
    "cafe-20260318-rss-67a7cd": {
        "title": "There's a Hole in the Student Council Too! Vol.12: \"Love stories are also progressing♪\"",
        "description": "Muchimaro's manga 'Seitokai nimo Ana wa Aru!' Volume 12 was released on the 17th. On Halloween night, a costumed Komaro visits Ume's house for a private Halloween party for two."
    },
    "cafe-20260318-rss-8a59b2": {
        "title": "The Vampire Wants to be Blood-Taken Final Vol.3: 'The fate that awaits after the blood-taking fetish is exposed'",
        "description": "Takeya Takekake's manga 'Kyuuketsuki-san wa Chitoraretai' final volume 3 was released on the 17th. The story concludes as the characters head to the sea and secrets are revealed."
    },
    "cafe-20260318-rss-98908b": {
        "title": "Circle nikukyu 'Yoduki Sisters' Emergency Rations 6': 'Doing the deed in the abandoned school building after class'",
        "description": "Circle nikukyu's new Comitia 155 release arrives at Melonbooks Akihabara. A story about Kana, who acquired Succubus syndrome, and their risky encounters after school."
    },
    "cafe-20260318-rss-416f2a": {
        "title": "[Digital Doujinshi Intro] Gloomy Zaibatsu Heir Makes Babies with Busty Maids: 'I Want to Impregnate Maids Even if I\\'m Unpopular! Omnibus'",
        "description": "A massive 1000+ page CG collection of a gloomy heir dedicating himself to making babies with various busty maids. Features a range of interactions."
    },
    "cafe-20260318-rss-d20801": {
        "title": "Writhe, Adam-kun Vol.7: 'Finally crossing the line with their stepbrother!?'",
        "description": "Toyo's manga 'Modaete yo, Adam-kun' Volume 7 was released in Akihabara on the 16th. Kasari, the younger sister, finally confesses her feelings."
    },
    "cafe-20260318-rss-211fa2": {
        "title": "Ayatsuri Calendar Vol.1: 'Doing whatever you want with schedules using a calendar app♥'",
        "description": "Tatsuki Aikawa's manga 'Ayatsuri Calendar' Volume 1 was released in Akihabara on the 16th. A story about freely manipulating an annoying boss's schedule with a magic calendar app."
    },
    "cafe-20260318-rss-b3c572": {
        "title": "Comic Adaptation 'Comrade Girl, Shoot the Enemy' Vol.3: 'The all-female sniper platoon heads to the fierce battleground'",
        "description": "Yuki Kamatani's manga adaptation of Toma Aisaka's novel 'Doushi Shoujo yo, Teki wo Ute' Volume 3 was released in Akihabara on the 16th. The all-female sniper platoon faces brutal reality on the frontlines."
    }
}

with open('data/staging/split/akiba-blog.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    item_id = item['id']
    if item_id in translations:
        item['title'] = translations[item_id]['title']
        item['description'] = translations[item_id]['description']

with open('data/staging/split/akiba-blog.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied successfully to akiba-blog.json.')
