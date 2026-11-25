INSERT INTO riding_rings VALUES ('OUT','河西露天围场','sand',8,false),('COV','棚下纤维围场','fiber',5,true),('LOW','课前小圈','sand',3,false) ON CONFLICT DO NOTHING;
INSERT INTO ring_walks VALUES
 ('T01','OUT','2026-11-08',12,7,30,'clear',false,'11 月巡场归档'),
 ('T02','OUT','2026-11-09',31,1,39,'clear',true,'11 月巡场归档'),
 ('T03','OUT','2026-11-10',5,9,10,'clear',false,'11 月巡场归档'),
 ('T04','OUT','2026-11-11',55,3,55,'clear',true,'11 月巡场归档'),
 ('T05','COV','2026-11-12',8,8,62,'clear',false,'11 月巡场归档'),
 ('T06','COV','2026-11-13',29,2,20,'clear',true,'11 月巡场归档'),
 ('T07','COV','2026-11-15',8,9,11,'clear',false,'11 月巡场归档'),
 ('T08','OUT','2026-11-16',30,2,30,'clear',true,'11 月巡场归档'),
 ('T09','COV','2026-11-17',11,5,30,'clear',false,'11 月巡场归档'),
 ('T10','OUT','2026-11-18',41,1,20,'clear',true,'11 月巡场归档'),
 ('W20','OUT','2026-11-24',45,4,42,'review',NULL,'周二 08:00 巡场.csv'),
 ('W22','COV','2026-11-24',4,6,28,'clear',NULL,'周二 08:00 巡场.csv'),
 ('W25','LOW','2026-11-24',1,4,10,'clear',NULL,'周二 08:00 巡场.csv') ON CONFLICT DO NOTHING;
INSERT INTO lessons VALUES ('L09','初级 6 班',4,'2026-11-24T09:00:00+08:00','OUT','scheduled'),
 ('L10','双人基础课',2,'2026-11-24T10:00:00+08:00','OUT','scheduled'),
 ('L14','姿态小组',3,'2026-11-24T14:00:00+08:00','COV','scheduled') ON CONFLICT DO NOTHING;
