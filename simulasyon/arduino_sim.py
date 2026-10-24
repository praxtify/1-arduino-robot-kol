"""Arduino kodunu MuJoCo'da oynat: al_birak.ino okunur, servolar koddaki hız ve ivmeyle hareket eder.

Gerçek kol olmadan kodu denemek için. Koddan okunanlar: HIZ, IVME, DURUS tablosu ve setup()'taki beklemeler.
Her git() çağrısında altı servo aynı anda yola çıkar; STS3215'in yamuk hız profili (önce ivmelen, sabit hızla git,
yavaşlayarak dur) taklit edilir. En yavaş servo varınca bir sonraki duruşa geçilir, tıpkı ReadMove döngüsü gibi.
Tutma ve bırakma tamamen fizik motorunun temas hesabıyla olur.

Çalıştırmak için (repo klasöründe):
    python simulasyon/arduino_sim.py               # 3D pencereyle
    python simulasyon/arduino_sim.py --ekransiz    # pencere açmadan, yalnız sonucu yazdır
macOS'ta pencereli çalıştırmak için python yerine mjpython kullan.
"""
import re  # Koddan sayıları okumak için
import sys  # Komut satırı
import time  # Gerçek zamanla eşitleme

import mujoco  # Fizik motoru
import mujoco.viewer  # 3D pencere
import numpy as np  # Sayılar

import sahne  # Kol + kutu sahnesi

INO = sahne.REPO / "al_birak/al_birak.ino"  # Videodaki Arduino kodu
ADIM_RAD = 4096 / (2 * np.pi)  # 1 radyan kaç servo adımı (bir tur 4096 adım)


def ino_oku(yol):
    """Arduino kodundan HIZ, IVME, DURUS (+ satır yorumları) ve setup()'taki beklemeleri oku."""
    t = yol.read_text(encoding="utf-8")
    sayilar = lambda s: [int(x) for x in re.findall(r"-?\d+", s)]
    hiz = sayilar(re.search(r"HIZ\[6\]\s*=\s*\{([^}]*)\}", t).group(1))  # adım / sn
    ivme = [a * 100 for a in sayilar(re.search(r"IVME\[6\]\s*=\s*\{([^}]*)\}", t).group(1))]  # × 100 adım / sn²
    govde = re.search(r"DURUS\[\]\[6\]\s*=\s*\{(.*?)\n\};", t, re.S).group(1)
    durus, adlar = [], []
    for satir in govde.splitlines():
        m = re.search(r"\{([^}]*)\}", satir)
        if m:
            durus.append(sayilar(m.group(1)))
            adlar.append(satir.split("//")[-1].strip())
    setup = t[t.index("void setup()"):]
    acilis, bekle = [int(x) / 1000 for x in re.findall(r"delay\((\d+)\)", setup)]  # açılış + her duruştan sonra
    git_bekle = int(re.search(r"SyncWritePosEx[^\n]*\n\s*delay\((\d+)\)", t).group(1)) / 1000  # paket sonrası
    return {"hiz": hiz, "ivme": ivme, "durus": durus, "adlar": adlar,
            "acilis": acilis, "bekle": bekle, "git_bekle": git_bekle}


def profil_suresi(fark, v, a):
    """Yamuk hız profili: fark adımı, en fazla v adım/sn hız ve a adım/sn² ivmeyle kaç saniyede gider."""
    fark = abs(fark)
    if fark == 0:
        return 0.0
    if fark < v * v / a:
        return 2 * np.sqrt(fark / a)  # Tepe hıza ulaşmadan (üçgen profil)
    return fark / v + v / a


def profil_konum(p0, p1, v, a, t):
    """Profilde t anındaki konum (adım)."""
    d = p1 - p0
    D = abs(d)
    T = profil_suresi(D, v, a)
    if D == 0 or t >= T:
        return float(p1)
    if D < v * v / a:  # Üçgen: yarısında hızlan, yarısında yavaşla
        x = 0.5 * a * t * t if t < T / 2 else D - 0.5 * a * (T - t) ** 2
    else:  # Yamuk: hızlan, sabit git, yavaşla
        ta = v / a
        if t < ta:
            x = 0.5 * a * t * t
        elif t < T - ta:
            x = 0.5 * a * ta * ta + v * (t - ta)
        else:
            x = D - 0.5 * a * (T - t) ** 2
    return p0 + np.sign(d) * x


def program(ino):
    """setup()'taki döngünün zaman çizelgesi: her git() için (başlama, bitiş, önceki duruş, hedef duruş, ad)."""
    t, onceki, out = ino["acilis"], ino["durus"][0], []
    for hedef, ad in zip(ino["durus"], ino["adlar"]):
        T = max(profil_suresi(h - o, v, a) for h, o, v, a in zip(hedef, onceki, ino["hiz"], ino["ivme"]))  # En yavaş servo
        bitis = t + max(T, ino["git_bekle"]) + 0.01  # ReadMove 10 ms'de bir sorulur
        out.append((t, bitis, onceki, hedef, ad))
        t, onceki = bitis + ino["bekle"], hedef
    return out


def servo_hedefi(ino, prog, t):
    """t anında altı servonun profil konumu (adım) ve o anki duruşun adı."""
    for i, (b, e, p0, p1, ad) in enumerate(prog):
        if t < b:
            return np.array(p0, float), prog[i - 1][4] if i else "açılış"
        if t < e:
            return np.array([profil_konum(a, c, v, ac, t - b)
                             for a, c, v, ac in zip(p0, p1, ino["hiz"], ino["ivme"])]), ad
    return np.array(prog[-1][3], float), prog[-1][4]


def main():
    ekransiz = "--ekransiz" in sys.argv
    ino = ino_oku(INO)
    prog = program(ino)
    sure = prog[-1][1] + 1.0  # Program bitince 1 sn daha (kutu otursun)

    model = sahne.build_model()
    data = mujoco.MjData(model)
    kutu = model.body("kutu").id
    data.qpos[:6] = (np.array(ino["durus"][0]) - 2048) / ADIM_RAD  # Kol koddaki ilk duruşta başlar
    data.ctrl[:6] = data.qpos[:6]
    mujoco.mj_forward(model, data)

    def adim_at():
        """Servo hedeflerini motorlara ver, fiziği 5 ms ilerlet; o anki duruşun adını döndür."""
        hedef, ad = servo_hedefi(ino, prog, data.time)
        data.ctrl[:6] = (hedef - 2048) / ADIM_RAD  # Servo adımı → eklem açısı
        mujoco.mj_step(model, data)
        return ad

    if ekransiz:
        while data.time < sure:
            adim_at()
    else:
        font, kose = mujoco.mjtFontScale.mjFONTSCALE_200, mujoco.mjtGridPos.mjGRID_TOPLEFT
        with mujoco.viewer.launch_passive(model, data) as viewer:
            baslangic = time.time()
            while viewer.is_running() and data.time < sure:
                ad = adim_at()
                viewer.set_texts((font, kose, f"Durus: {ad}", f"t = {data.time:.1f} sn"))
                viewer.sync()
                fark = data.time - (time.time() - baslangic)  # Gerçek zamandan ne kadar öndeyiz
                if fark > 0:
                    time.sleep(fark)

    p = data.xpos[kutu]
    uzaklik = np.linalg.norm(p[:2] - sahne.DROP_SPOT) * 1000  # Kutunun hedef merkezine yatay uzaklığı (mm)
    print(f"{len(prog)} duruş, {prog[-1][1]:.1f} sn · kutu hedefin ortasına {uzaklik:.1f} mm yakın bırakıldı")


if __name__ == "__main__":
    main()
