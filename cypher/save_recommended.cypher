// บันทึกผลแนะนำ 3 อันดับแรกของทุกคนเป็นเส้น RECOMMENDED (ใช้สูตรแบบ notebook: นับเส้นทาง)
// ใน Streamlit ใช้ปุ่ม "บันทึกผลแนะนำลง Aura" ในหน้า Admin แทนได้ (ใช้สูตร hybrid)

MATCH ()-[r:RECOMMENDED]->() DELETE r;

MATCH (me:Person)-[:LIKES]->(:Style)<-[:LIKES]-(other:Person)-[:LIKES]->(rec:Style)
WHERE other <> me
  AND NOT EXISTS { MATCH (me)-[:LIKES]->(rec) }
WITH me, rec, count(*) AS score
ORDER BY score DESC, rec.style_id
WITH me, collect({rec: rec, score: score})[0..3] AS top
UNWIND range(0, size(top) - 1) AS i
WITH me, top[i].rec AS rec, top[i].score AS score, i + 1 AS rank
MERGE (me)-[r:RECOMMENDED]->(rec)
SET r.score = score, r.rank = rank;

// ดูผล
MATCH path = (:Person {person_id:'P01'})-[:LIKES|RECOMMENDED]->(:Style)
RETURN path;
