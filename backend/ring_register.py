def register(cx):
    return cx.execute('''
        SELECT r.*, w.code AS walk, w.observed, w.barrier, c.close_recommended
        FROM riding_rings r LEFT JOIN LATERAL (
            SELECT * FROM ring_walks WHERE ring=r.code AND outcome IS NULL ORDER BY observed DESC,code DESC LIMIT 1
        ) w ON true LEFT JOIN ring_calls c ON w.code=c.walk
        ORDER BY r.sheltered DESC,r.title
    ''').fetchall()
