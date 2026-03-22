import json

# Update sources.json
with open('data/sources.json', 'r', encoding='utf-8') as f:
    sources_data = json.load(f)

for source in sources_data['sources']:
    if source['id'] == '4gamer':
        source['categories'] = ['game']

with open('data/sources.json', 'w', encoding='utf-8') as f:
    json.dump(sources_data, f, ensure_ascii=False, indent=4)

# Update entries.json
with open('data/entries.json', 'r', encoding='utf-8') as f:
    entries_data = json.load(f)

for entry in entries_data['entries']:
    if entry.get('_source_id') == '4gamer':
        entry['category'] = 'game'

with open('data/entries.json', 'w', encoding='utf-8') as f:
    json.dump(entries_data, f, ensure_ascii=False, indent=2)

print("Updated 4gamer category to 'game' in both sources.json and entries.json")
