"""Nguong phien (05/10/2026): gia lam tron LEN theo buoc gia, tinh tu GIA THAM CHIEU;
KL = dung muc bo may can (TB20 gom ca phien toi). Moi gia tri tra ve phai VUA DU qua
dieu kien cua signal_spec.evaluate, va mot buoc gia / 1 co phieu thap hon thi TRUOT."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import signal_spec as SP

def qua_gia(p, ref, thr):
    return SP.ret32(SP.f32(p), SP.f32(ref)) >= SP.f32(thr)

def main():
    # ca that 05/10/2026
    assert SP.gia_can(44600, 0.0560000017285347, 'HOSE') == 47100, 'DGW ex-co tuc'
    assert SP.gia_can(45600, 0.056, 'HOSE') == 48200, '48,15 cu la TRUOT'
    assert not qua_gia(48150, 45600, 0.056)
    assert SP.gia_can(9500, 0.056, 'HOSE') == 10050       # vuot moc 10.000 -> buoc 50
    assert SP.gia_can(17700, 0.088, 'HNX') == 19300
    assert SP.kl_can({'vol_s19': 38953000.0, 'vol_c19': 19}, 2.0) == 4328111
    rnd = random.Random(7)
    for _ in range(3000):
        ex = rnd.choice(['HOSE', 'HNX', 'UPCOM'])
        thr = rnd.choice([0.056, 0.0560000017285347, 0.088])
        ref = rnd.randrange(1000, 300000, 10 if ex == 'HOSE' else 100)
        p = SP.gia_can(ref, thr, ex)
        assert qua_gia(p, ref, thr), (ref, thr, ex, p)
        b = SP.buoc_gia(p - 1, ex)
        assert p % SP.buoc_gia(p, ex) == 0 or p % b == 0, (ref, p)
        assert not qua_gia(p - b, ref, thr), (ref, thr, ex, p)
    for _ in range(2000):
        c = rnd.randint(16, 19); s = float(rnd.randint(10**5, 10**9))
        v = SP.kl_can({'vol_s19': s, 'vol_c19': c}, 2.0)
        ok = lambda x: SP.ge32(SP.div32(SP.f32(float(x)), SP.pos_or_nan(SP.mean20(s, c, SP.f32(float(x))))), 2.0)
        assert ok(v) and not ok(v - 1), (s, c, v)
    print('test_nguong_phien: DAT')

if __name__ == '__main__':
    main()
