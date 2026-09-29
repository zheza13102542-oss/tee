// รหัสคนห้ามซ้ำ
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

// รหัสทรงผมห้ามซ้ำ
CREATE CONSTRAINT style_id_unique IF NOT EXISTS
FOR (h:Style) REQUIRE h.style_id IS UNIQUE;
