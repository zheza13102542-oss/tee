// Explainable Hybrid Hair Style Recommendation
// Parameters: $person_id, $limit
// ลองรันใน Aura ได้โดยใส่ :param person_id => 'P01'; และ :param limit => 6; ก่อน
// เริ่มจากคนที่ต้องการคำแนะนำ และทรงผมทุกทรงที่เขายังไม่ได้ชอบ
MATCH (u:Person {person_id:$person_id})
MATCH (h:Style)
WHERE NOT EXISTS { (u)-[:LIKES]->(h) }

// 1) Collaborative signal: คนที่ชอบทรงเดียวกับ u และชอบทรง h ด้วย
//    u -> ทรงที่ชอบ (shared) <- คนอื่น (o) -> h
OPTIONAL MATCH (u)-[:LIKES]->(shared:Style)<-[:LIKES]-(o:Person)-[:LIKES]->(h)
WHERE o <> u
WITH h,
     count(DISTINCT o) AS similar_people,
     [x IN collect(DISTINCT o.name) WHERE x IS NOT NULL][0..3] AS similar_names,
     count(DISTINCT shared) AS shared_styles,
     [x IN collect(DISTINCT shared.name) WHERE x IS NOT NULL] AS shared_names

// 2) Popularity + score signal: ทรง h มีคนชอบกี่คน คะแนนเฉลี่ยเท่าไร
OPTIONAL MATCH (:Person)-[l:LIKES]->(h)
WITH h, similar_people, similar_names, shared_styles, shared_names,
     count(l) AS popularity,
     avg(l.score) AS avg_score

// 3) รวมเป็นคะแนนเดียว (สูตรแบบเดียวกับงานอาจารย์ ปรับให้เข้ากับข้อมูลทรงผม)
WITH h, similar_people, similar_names, shared_styles, shared_names,
     popularity, coalesce(avg_score, 0.0) AS avg_score,
     (similar_people * 3.0) +
     (shared_styles * 2.0) +
     (popularity * 0.20) +
     (coalesce(avg_score, 0.0) * 0.25) AS score

// ตัดทรงที่ไม่มีหลักฐานอะไรเลย (ไม่มีใครชอบ)
WHERE similar_people > 0 OR popularity > 0

RETURN h.style_id AS style_id, h.name AS style,
       similar_people, similar_names, shared_styles, shared_names,
       popularity, round(avg_score * 100) / 100.0 AS avg_score,
       round(score * 100) / 100.0 AS score
ORDER BY score DESC, h.style_id
LIMIT $limit;
