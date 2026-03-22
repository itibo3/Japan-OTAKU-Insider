import json

translations = {
    "anime-20260318-rss-758ab9": {
        "title": "Chika Umino Appears on Expanded Special of 'Naoki Urasawa's Manben neo' on NHK BS",
        "description": "A documentary program featuring Chika Umino, 'Naoki Urasawa's Manben neo', will air an expanded special on March 19th on NHK BS."
    },
    "anime-20260318-rss-9d5899": {
        "title": "'Steel Ball Run' Anime Streaming Starts Tomorrow, New Scene Cuts Revealed",
        "description": "New scene cuts from the anime 'Steel Ball Run: JoJo's Bizarre Adventure' based on Hirohiko Araki's original work have been released."
    },
    "anime-20260318-rss-10e437": {
        "title": "One Year Until School Closure: A Youth Story Capturing the School Across Four Seasons",
        "description": "Nishina's manga volume 'Haru no Hikari ni Nomaretemo' (Even if Swallowed by the Spring Light) was released today, March 18th."
    },
    "anime-20260318-rss-8d9113": {
        "title": "Dark Fantasy of a Little Girl with Highly Poisonous Lips: 'Kiss of the Amphisbaena'",
        "description": "Tetora Wakamiya's new serialization started in Monthly G Fantasy. A dark fantasy about Blue, a girl born with poisonous lips."
    },
    "anime-20260318-rss-6d0f9c": {
        "title": "Kyoko Hikawa's 'From Far Away' Gets TV Anime! Directed by Noriyuki Abe",
        "description": "To commemorate the 35th anniversary of Kyoko Hikawa's 'Kanata Kara', a TV anime adaptation has been announced with a special PV."
    },
    "anime-20260318-rss-e33ebe": {
        "title": "Anime 'Matakoro' Main PV & Visual Released, Broadcasting Starts April 2nd",
        "description": "The TV anime 'Mata Korosarete Shimattano desu ne, Tantei-sama' will begin broadcasting on April 2nd. The OP theme is by Tajigen Seigyo Kikou Yodaka."
    },
    "anime-20260318-rss-de91bb": {
        "title": "An Unknown Academy on the Dark Side of Tokyo: Exorcist Action 'Ura Tokyo no Osoroshidokoro'",
        "description": "KOJIRO's new manga serialization 'Ura Tokyo no Osoroshidokoro' started today in Weekly Shonen Magazine issue 16."
    },
    "anime-20260318-rss-351a18": {
        "title": "Yonehiko Kitagawa Passes Away from Pneumonia, Known as Chairman in 'Kinnikuman'",
        "description": "Voice actor Yonehiko Kitagawa, known for his iconic roles such as the Chairman in Kinnikuman, passed away on March 5th at 94."
    },
    "anime-20260318-rss-e22caa": {
        "title": "A Princess Turned Chicken & Clueless Emperor Seek True Love in 'Princess of the Birdcage'",
        "description": "Volume 1 of DOHA's 'Torikago no Ohimesama', based on mieun-lee's original work, was released today."
    },
    "anime-20260318-rss-62a9b7": {
        "title": "A Dropout Hero Saves the World with 'Holy Light' in Comedy Adventure 'Seijun Ecstasy'",
        "description": "Volume 1 of Saku Kimura's 'Seijun Ecstasy: I'll Beat the Demons in a Room You Can't Leave Unless You Do XX' was released today."
    }
}

file_path = 'data/staging/split/natalie-anime.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    item_id = item['id']
    if item_id in translations:
        item['title'] = translations[item_id]['title']
        item['description'] = translations[item_id]['description']

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Translation applied to natalie-anime.json.')
