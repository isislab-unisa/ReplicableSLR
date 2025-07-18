from pybibx.Snowballing.Scopus.snawball import SnowballingEngine

engine = SnowballingEngine(api_key="YOUR_SCOPUS_API_KEY")
data = engine.snowball("2-s2.0-85085004285")  # EID

print("Title:", data['title'])
print("Total Citations:", data['citations'])
print("Forward (citanti):", len(data['forward']))
print("Backward (citati):", len(data['backward']))
