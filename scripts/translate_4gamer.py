import json

translations = {
    "anime-20260318-rss-48cb34": {
        "title": "'Apex Legends': 3 Special Gunpla to Commemorate Gundam Collab. Pre-orders Start March 19",
        "description": "EA Japan announced special Gunpla models to celebrate the ongoing Gundam series collaboration in 'Apex Legends'."
    },
    "anime-20260318-rss-c55d55": {
        "title": "'Chaos Zero Nightmare': Final Chapter 'Heart, Promise' of Season 2 Implemented. New Fighter 'Rita' Appears",
        "description": "Smilegate implemented the final chapter of Season 2 in the roguelike RPG 'Chaos Zero Nightmare', adding new 5-star fighters."
    },
    "anime-20260318-rss-b55b3e": {
        "title": "'Uma Musume Pretty Derby': New 3-Star Victoire Pisa Coming March 19",
        "description": "Cygames announced the addition of a new 3-star character, Victoire Pisa, to the training game 'Uma Musume Pretty Derby' on March 19th."
    },
    "anime-20260318-rss-e1c856": {
        "title": "Persuade Grandpa for $10 Million No Matter What. New Visual Novel 'Scam Grandpa' Demo Released",
        "description": "BRBDrama released a demo for 'Scam Grandpa', a black humor visual novel where a grandchild tries to extract 10 million dollars from a miserly grandfather."
    },
    "anime-20260318-rss-e60b5a": {
        "title": "Arcade Archives Version of 'Garuka' (Devastators) Releasing March 19. 1988 Konami STG",
        "description": "Hamster announced the Arcade Archives release of Konami's 1988 vertical scrolling shooter 'Garuka' (Devastators) for March 19th."
    },
    "anime-20260318-rss-974c65": {
        "title": "Enjoy a Puzzle Game at Mos Premium Stores: 'Mos Premium Theater' Preview Report",
        "description": "Mos Burger and Sega XD will host an interactive puzzle event from March 20th to May 6th, where participants solve codes to complete a phantom recipe."
    },
    "anime-20260318-rss-a2efca": {
        "title": "'Katamari' Series Celebrates its 22nd Anniversary. Plentiful Goods Info Revealed",
        "description": "Bandai Namco Entertainment revealed new product information to celebrate the 22nd anniversary of the 'Katamari' series, including capsule toys."
    },
    "anime-20260318-rss-6a0b69": {
        "title": "Merge Puzzle 'Planet Nine' Where You Shoot and Combine Planets Gets Steam Store Page",
        "description": "Indie developer Haizai published the Steam store page for 'Ninth Planet', a planet merge puzzle game with billiards-like mechanics."
    },
    "anime-20260318-rss-43ce0b": {
        "title": "PS5 Digital Edition Console Bundle with Two DualSense Controllers Launching April 24",
        "description": "SIE announced a bundle containing the PS5 Digital Edition console and two DualSense wireless controllers, set to release on April 24th."
    },
    "anime-20260318-rss-d9860c": {
        "title": "Strategy Board Game 'Kakegurui ALL IN' Starts Advance Play Campaign on March 19",
        "description": "CTW announced an advance play campaign starting March 19th for 'Kakegurui ALL IN', an upcoming game on the G123 service."
    }
}

file_path = 'data/staging/split/4gamer.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    item_id = item['id']
    if item_id in translations:
        item['title'] = translations[item_id]['title']
        item['description'] = translations[item_id]['description']

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied to 4gamer.json.')
