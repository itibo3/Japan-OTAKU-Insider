import json

translations = {
    "figure-20260318-rss-41181d": {
        "title": "'Resident Evil: Requiem' Capcom Figure Builder Creator's Model Grace Ashcroft 1/6 Scale Figure",
        "description": "Check out Capcom's new Figure Builder Creator's Model for Grace Ashcroft in 1/6 scale with newly taken photos and videos."
    },
    "figure-20260318-rss-042f6a": {
        "title": "Empress from TV Anime 'Black★★Rock Shooter DAWN FALL' Gets a 1/4 Scale Figure!",
        "description": "From 'Black★★Rock Shooter DAWN FALL', Empress joins Prime 1 Studio's Ultimate Premium Masterline. Releasing July-October 2027."
    },
    "figure-20260318-rss-72f7c6": {
        "title": "PLAfig. No.PF-04 Godzilla (2001) Plastic Model Kit [Aoshima]",
        "description": "The terrifying King of the Monsters, Godzilla (2001), appears as a plastic model kit in the new brand 'PLAfig.' by Aoshima."
    },
    "figure-20260318-rss-876097": {
        "title": "From 'SSSS.GRIDMAN', 'Rikka Takarada & Akane Shinjo' Get Figures Based on Toridamono's Illustration!",
        "description": "Rikka Takarada & Akane Shinjo from 'SSSS.GRIDMAN' are getting 1/7 scale figures releasing in February 2027 by Good Smile Company."
    },
    "figure-20260318-rss-175e49": {
        "title": "From the Game 'Genshin Impact', 'Columbina' in a Pure White Dress Gets a 1/8 Scale Figure!",
        "description": "From 'Genshin Impact', 'Columbina: Joyful Gathering Ver.' comes as a 1/8 scale figure scheduled for release in October 2026."
    },
    "figure-20260318-rss-d9708d": {
        "title": "March 2026 3rd Week: Delivering the AmiAmi Akihabara Radio Kaikan Store Exhibition!",
        "description": "Check out the exhibition state at AmiAmi Akihabara Radio Kaikan Store for the 3rd week of March 2026, featuring trending characters."
    },
    "figure-20260318-rss-a7f2f2": {
        "title": "From 'Arknights: Endfield', 'Yvon' Gets a Figure Surrounded by Multiple Layered Displays!",
        "description": "From 'Arknights: Endfield', Yvon appears as a 1/7 scale figure scheduled for release in November 2026."
    },
    "figure-20260318-rss-b74474": {
        "title": "From TV Anime 'Oshi no Ko', Hologram BIG Stands & Acrylic Keychains Available from AmiAmi!",
        "description": "TV Anime 'Oshi no Ko' goods featuring Hologram BIG Stands and Acrylic Keychains with 6 lineups each are scheduled for June 2026."
    },
    "figure-20260318-rss-030119": {
        "title": "From the Drama 'Fallout', 'Lucy MacLean' Gets 1/4 Scale Figure! Pre-orders Open at Prime 1 Studio!",
        "description": "From Prime 1 Studio's Real Elite Masterline comes Lucy MacLean from the 'Fallout' drama. Scheduled for release June-September 2027."
    },
    "figure-20260318-rss-ee1b06": {
        "title": "'Girls' Frontline 2: Exilium' Springfield Queen Under the Lights Ver. 1/7 Scale Figure [Kotobukiya]",
        "description": "AmiAmi x Kotobukiya review project explores the highly anticipated 1/7 scale figure of Springfield Queen Under the Lights Ver."
    }
}

file_path = 'data/staging/split/amiami-news.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    item_id = item['id']
    if item_id in translations:
        item['title'] = translations[item_id]['title']
        item['description'] = translations[item_id]['description']

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied to amiami-news.json.')
