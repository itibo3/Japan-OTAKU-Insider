import json
import glob

translations = {
    # nitroplus-blog
    "anime-20260318-rss-5117ac": {
        "title": "Nitroplus Jobs [Part 4: Game Development]",
        "description": "Hello! Nitro-kun here. We are currently recruiting staff to help with game development. No experience needed! Must love Nitroplus games!"
    },
    "anime-20260318-rss-3be999": {
        "title": "Nitroplus Jobs [Part 3: Daily Time Schedule]",
        "description": "Nice to meet you! I'm Morio, a newbie who joined in May. I work in the promo and marketing department planning events."
    },
    "anime-20260318-rss-e38749": {
        "title": "Nitroplus Jobs [Part 2: Newbie Edition]",
        "description": "Nice to meet you, I'm Ronriko. My hobby is finding the origins of internet memes. I'll introduce what a newbie does at the company."
    },
    "anime-20260318-rss-83772b": {
        "title": "Nitroplus Jobs [Part 1: Event Planning & Management]",
        "description": "Nice to meet you, I'm K.K. We've decided to introduce the jobs of Nitroplus staff on this blog. This time, it's Event Planning & Management."
    },
    "anime-20260318-rss-d33c8e": {
        "title": "Congratulations! Comic Market 100!!",
        "description": "Hello! It's been a while, but Nitro-kun from PR here, now reborn as 'Nitro-kun NEO'! Our staff image has also been renewed."
    },
    "anime-20260318-rss-9209d4": {
        "title": "'Smile of the Arsnotoria' is Now Available!",
        "description": "Have you played 'Smile of the Arsnotoria' yet? It's an authentic fantasy RPG where you become a wizard and fight alongside girls!"
    },
    "anime-20260318-rss-d25e6b": {
        "title": "'The Ugly Mojika Child' is Now on Sale!!",
        "description": "Hello! Katatsumuri here, PR for 'Minikui Mojika no Ko'. Our mind-and-body violating ADV is finally on sale at PC game and online shops!"
    },
    "anime-20260318-rss-a84b20": {
        "title": "'The Ugly Mojika Child' Pre-orders Now Open!",
        "description": "Hello! Nekokan Masshigura here. It's getting hotter, feeling like summer. Speaking of summer, it's 'Minikui Mojika no Ko'!"
    },
    "anime-20260318-rss-7a3b50": {
        "title": "'Thunderbolt Fantasy: The Sword of Life and Death' Released Today!",
        "description": "'Thunderbolt Fantasy: Seishi Ikken' premieres today! The transcended martial arts puppet show returns with a big screen and rich 5.1ch sound!"
    },
    "anime-20260318-rss-ce3a3c": {
        "title": "'Full Metal Daemon Muramasa 8th Anniversary' Sansei (Swimsuit) Muramasa",
        "description": "Posting the 'Muramasa 8th Anniversary' illustration so I don't forget it. Released back on Oct 30, 2009. Still going strong on its 8th anniversary!"
    },

    # dengeki-hobby
    "figure-20260318-rss-b5eb03": {
        "title": "'Super Robot Wars OG' Weissritter Gets Action Figure in Kuro Kara Kuri Series! Pre-orders Open on Amazon",
        "description": "From 'Super Robot Wars OG', Excellen Browning's silver fallen angel Weissritter gets an action figure in the Kuro Kara Kuri series with built-in LED!"
    },
    "figure-20260318-rss-030116": {
        "title": "Idol 'Rino Yumetsuki' in Bunny Outfit Gets Figure! Normal Swimsuit Ver & Nearly Nude Adult Ver Released!!",
        "description": "Original figure 'Rino Yumetsuki' gets a 1/6 scale figure! Normal version by Bfull FOTS JAPAN and Adult version by Insight set for October 2026."
    },
    "figure-20260318-rss-be0018": {
        "title": "'Gundam Char's Counterattack' METAL ROBOT Spirits Sazabi 2nd Pre-order Lottery Decided! Starts March 19!",
        "description": "From 'Mobile Suit Gundam Char's Counterattack', the 2nd pre-order for METAL ROBOT Spirits Sazabi will be sold via lottery starting March 19."
    },
    "figure-20260318-rss-d28e96": {
        "title": "Highlighting March 18 Kindle Comics: 'Uma Musume Pretty Derby Umamusumeshi' Vol.7, 'Jaja' Vol.39, etc!",
        "description": "Picking up Kindle comics released on March 18 on Amazon Kindle Store, including 'Uma Musume' spin-off manga and more!"
    },
    "figure-20260318-rss-5bfdf7": {
        "title": "Machines from 'Kamen Rider' Series Join 'Machibouke' Gashapon Figures! Featuring Gouram and Auto Vajin!",
        "description": "Kamen Rider series machines join the 'Machibouke' gashapon line. Gouram, Auto Vajin, Lazer, and Code Zeroider are sculpted in melancholic poses."
    },
    "figure-20260318-rss-28138c": {
        "title": "Official Apparel for Disney & Pixar's Latest 'When I Become a Beaver' on Sale via Amazon Merch on Demand!",
        "description": "Cute designs! Official T-shirts and sweatshirts for Disney & Pixar's latest 'When I Become a Beaver' are available on Amazon Merch on Demand!"
    },
    "figure-20260318-rss-8d6275": {
        "title": "'Honkai: Star Rail' Cute Sparkle Hugging Plush Gets Deformed Figure in 'Huggy Good Smile'! Pre-orders at AmiAmi",
        "description": "Attention to her adorable expression! From 'Honkai: Star Rail', Sparkle Hugging Plush gets a deformed figure in the 'Huggy Good Smile' series."
    },
    "figure-20260318-rss-198106": {
        "title": "Sanrio Characters Design Capsule Toys 'minimini Folding Table Part 2' and 'minimini Rug-style Keychain' Released!",
        "description": "Two new Sanrio capsule toys launching sequentially from late March. Combine the 'minimini Folding Table Part 2' and 'minimini Rug-style Keychain'."
    },
    "figure-20260318-rss-69ddce": {
        "title": "Two Medusa Girl Figures 'Green Viper' and 'Crimson Viper' from WE ART DOING! Pre-orders Open at AmiAmi!",
        "description": "What lies beneath the snakes...? Two Medusa girls 'Green Viper' and 'Crimson Viper' get figures from WE ART DOING!"
    },
    "figure-20260318-rss-6705a1": {
        "title": "'Chiikawa' Smartphone App 'Chiikawa Pocket' Official Goods Vol.2 Launch April 10! Many New Items!!",
        "description": "'Chiikawa's' first smartphone app 'Chiikawa Pocket' official goods Vol.2! New goods like mascots, can badges, and acrylic stands featuring fruit motifs."
    },

    # prtimes-kotobukiya
    "figure-20260318-rss-c6fafa": {
        "title": "Digital Figure 'HoloModels' First Overseas Expansion: Sales Start at Animate Stores & EC in South Korea",
        "description": "Gugenka announced the start of sales for digital figure 'HoloModels' in South Korea starting March 18, 2026."
    },
    "figure-20260318-rss-b3e303": {
        "title": "Gugenka Creates Immersive WebAR Photo Spot for 'My Melody & Kuromi' Exhibition Held Until Feb 2026",
        "description": "Gugenka produced an immersive photo spot using WebAR for the 'My Melody & Kuromi' exhibition held at the Tokyo Anime Center."
    },
    "figure-20260318-rss-64c7f9": {
        "title": "Holiday Shows Sold Out: 'SNOW MIKU 2026' Wotaru-za Digital Show powered by XREAL Event Report",
        "description": "Gugenka reported huge success at the 'SNOW MIKU 2026 Digital Show powered by XREAL' held at Wing Bay Otaru."
    },
    "figure-20260318-rss-752dac": {
        "title": "Second 'Nekopara' Series: Maple, Cinnamon, Azuki, and Coconut HoloModels Now on Sale",
        "description": "Gugenka released the second batch of HoloModels for the popular 11th-anniversary series 'Nekopara', featuring Maple, Cinnamon, Azuki, and Coconut."
    },
    "figure-20260318-rss-55634e": {
        "title": "3D Spatial Video Platform 'Spatial Disc' Releases 'Love Live! Sunshine!!' Aqours: 4 Single Tracks & 4-Track Set",
        "description": "Gugenka released Spatial Discs featuring the school idol group Aqours from 'Love Live! Sunshine!!' on their 3D spatial video platform."
    },
    "figure-20260318-rss-c73595": {
        "title": "Belcook and Hapidanbui Turned into Digital Figures! AR-enjoyable 'HoloModels' & WebAR Content Released",
        "description": "Gugenka released digital figures of Belc's character 'Belcook' and Sanrio's 'Hapidanbui' on the HoloModels app."
    },
    "figure-20260318-rss-2b3d17": {
        "title": "Gugenka and Sanrio Jointly Develop LBE Content for 'and ST TOKYO' Flagship Store",
        "description": "Gugenka provided Location-Based Entertainment content at the 'and ST TOKYO' flagship store in Shibuya."
    },
    "figure-20260318-rss-cf7ff7": {
        "title": "Gugenka Provides Interactive MR Video Content at 'Assault Lily Last Bullet' 5th Anniversary Event",
        "description": "Gugenka debuted Mixed Reality (MR) video experiences at the 5th-anniversary event of the app game 'Assault Lily Last Bullet'."
    },
    "figure-20260318-rss-9ef368": {
        "title": "Shoot Everyday Life with Your Oshi! New Version of 'HoloModels' Officially Released",
        "description": "Gugenka officially released a new version of the 'HoloModels' app, allowing users to carry and photograph their favorite digital figures on a smartphone."
    },
    "figure-20260318-rss-72aca4": {
        "title": "Gugenka Exhibits at 'SNOW MIKU 2026', Deploying Cutting-Edge XREAL Digital Show and Interactive Wall",
        "description": "Gugenka exhibited at 'SNOW MIKU 2026', organizing the digital show powered by XREAL at Wotaru-za and an interactive wall for attendees."
    }
}

for json_file in ['data/staging/split/nitroplus-blog.json', 'data/staging/split/dengeki-hobby.json', 'data/staging/split/prtimes-kotobukiya.json']:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for item in data:
        item_id = item['id']
        if item_id in translations:
            item['title'] = translations[item_id]['title']
            item['description'] = translations[item_id]['description']
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied to nitroplus-blog, dengeki-hobby, prtimes-kotobukiya.')
