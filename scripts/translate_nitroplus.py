import json
import glob

translations = {
    # nitroplus-news
    "anime-20260318-rss-f84ae2": {
        "title": "'Touken Ranbu Medi Nui Collection: Toukabu / Tousute' Official Pre-orders Open March 16!",
        "description": "The 2nd and 3rd lineup of the official Touken Ranbu ONLINE media mix plushies will start pre-orders on the Nitroplus official store."
    },
    "anime-20260318-rss-cdf7ec": {
        "title": "'Touken Ranbu Medi Nui Collection: Toumyu' Official Pre-orders Open March 9!",
        "description": "The 1st lineup of the official Touken Ranbu ONLINE media mix plushies (Toumyu) will start pre-orders on March 9."
    },
    "anime-20260318-rss-8801e7": {
        "title": "Anime Movie 'Puella Magi Madoka Magica: Walpurgisnacht Rising' Releases August 28!",
        "description": "The release date for the anime movie 'Walpurgis no Kaiten', written by Nitroplus's Gen Urobuchi, is set for August 28, 2026!"
    },
    "anime-20260318-rss-29c317": {
        "title": "'Touken Ranbu ONLINE' First Ice Show 'ICE BLADE' at Yoyogi National Stadium Oct 3-4!",
        "description": "The very first ice show for the sword raising simulation game 'Touken Ranbu ONLINE' will take place in Tokyo on October 3-4, 2026."
    },
    "anime-20260318-rss-f2df19": {
        "title": "Kabuki 'Touken Ranbu: Azuma Kagami Yuki no Midare' Blu-ray Released Today!",
        "description": "The Blu-ray for the second Touken Ranbu Kabuki adaptation, which garnered huge acclaim in Tokyo and Kyoto, is out today."
    },
    "anime-20260318-rss-a74764": {
        "title": "'Touken Ranbu Medi Nui Collection: Toukabu / Tousute' Releasing Early July!",
        "description": "New additions to the Touken Ranbu Medi Nui official plushie series featuring characters from the Kabuki and Stage play adaptations."
    },
    "anime-20260318-rss-994c64": {
        "title": "'Touken Ranbu ONLINE 10th Anniversary Memorial Book' Available on Official Store!",
        "description": "The gorgeous memorial book celebrating the 10th anniversary of Touken Ranbu ONLINE will be available on the official Nitroplus store."
    },
    "anime-20260318-rss-2032b0": {
        "title": "'Nitro Face Collection' Acrylic Keychains Available for Limited Pre-order!",
        "description": "Pre-orders have opened for the 'Nitro Face Collection' featuring 50 characters from Nitroplus, Nitro Origin, and Nitro Chiral works."
    },
    "anime-20260318-rss-4d256a": {
        "title": "Happy New Year!",
        "description": "Thank you for supporting Nitroplus content last year. Our staff will continue to do our best to deliver enjoyable content this year."
    },
    "anime-20260318-rss-1d32e2": {
        "title": "'Comiket 107' Held December 30-31!",
        "description": "Comic Market 107 will be held at Tokyo Big Sight! We've prepared a 2.4m giant gacha machine at the Nitroplus booth."
    },
    # nitroplus-goods
    "figure-20260318-rss-f460c4": {
        "title": "Touken Ranbu Medi Nui Collection: Toukabu",
        "description": "Official plushies of the Touken Ranbu ONLINE media mix works! The 2nd lineup features 6 characters from the Kabuki adaptation."
    },
    "figure-20260318-rss-8eacae": {
        "title": "Touken Ranbu Medi Nui Collection: Tousute",
        "description": "Official plushies of the Touken Ranbu ONLINE media mix works! The 3rd lineup features 6 characters from the Stage Play adaptation."
    },
    "figure-20260318-rss-91df2f": {
        "title": "Nitro Face Collection",
        "description": "Acrylic keychains featuring the 'faces' of 9 characters from Nitroplus works. Large size with roughly 10-13cm long sides."
    },
    "figure-20260318-rss-c51e0e": {
        "title": "Touken Ranbu Medi Nui Collection: Toumyu",
        "description": "Official plushies of the Touken Ranbu ONLINE media mix works! The 1st lineup features 6 characters from the Musical adaptation."
    },
    "figure-20260318-rss-080ecd": {
        "title": "Touken Ranbu ONLINE Official Setting Material Book Vol.5 'Touken Ranbu Kenran Zuroku Go'",
        "description": "The 5th official visual book covering the Touken Danshi from Touken Ranbu ONLINE is set for release in December 2025!"
    },
    "figure-20260318-rss-705dcc": {
        "title": "'Touken Ranbu Kenran Zuroku Go' Digital Edition",
        "description": "The digital edition of the 5th official visual book covering the Touken Danshi from Touken Ranbu ONLINE will be available simultaneously!"
    },
    "figure-20260318-rss-26108f": {
        "title": "The Choice History of 'Choices': How Nitroplus Scenario Writers Make Novel Games",
        "description": "A new paperback book discussing novel game scenario writing by Nitroplus writer Baio Shimokura is coming from Seikaisha!"
    },
    "figure-20260318-rss-12e4c2": {
        "title": "Blu-ray & DVD 'Thunderbolt Fantasy: Sword Seekers Final Chapter'",
        "description": "The finale of the martial arts fantasy puppet show 'Thunderbolt Fantasy Project' directed by Gen Urobuchi comes to Blu-ray & DVD."
    },
    "figure-20260318-rss-20ec02": {
        "title": "Digital Edition 'Thunderbolt Fantasy: Sword Seekers Final Chapter Pamphlet'",
        "description": "The official pamphlet for the final theatrical release of the Thunderbolt Fantasy Project is now available as a digital book!"
    },
    "figure-20260318-rss-05e2e2": {
        "title": "Digital Edition 'Thunderbolt Fantasy Gaiden Short Stories'",
        "description": "The short story collection originally distributed as a theatrical bonus for 'Thunderbolt Fantasy Final Chapter' is now a digital book!"
    }
}

for json_file in ['data/staging/split/nitroplus-news.json', 'data/staging/split/nitroplus-goods.json']:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for item in data:
        item_id = item['id']
        if item_id in translations:
            item['title'] = translations[item_id]['title']
            item['description'] = translations[item_id]['description']
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied to nitroplus-news & nitroplus-goods.')
