"""Arduino kodundaki DURUS tablosunu üret: her duruşta altı servonun hedef adımı.

Her duruşun eklem açıları MuJoCo'da ters kinematikle bulunur, STS3215 servo adımına çevrilir
(4096 adım = bir tur, 2048 = MuJoCo'daki sıfır açı) ve al_birak.ino'ya yapıştırılacak C dizisi olarak yazdırılır.

Çalıştırmak için (repo klasöründe):  python simulasyon/duruslar.py
"""
import mujoco  # Fizik motoru
import numpy as np  # Sayılar

import sahne  # Kol + kutu sahnesi, ters kinematik, plan

ADIM_RAD = 4096 / (2 * np.pi)  # 1 radyan kaç servo adımı (≈ 651,9)


def adim(q):
    """Eklem açısı (radyan) → servo adımı. Kalibrasyon: 2048 adım = MuJoCo'daki sıfır açı."""
    return int(round(2048 + q * ADIM_RAD))


def main():
    model = sahne.build_model()  # Robot + kutu + hedef bölge
    data, ghost = mujoco.MjData(model), mujoco.MjData(model)  # Sahne + hesap için hayalet kol
    site = model.site("gripperframe").id  # Tutucu ucundaki işaret noktası
    mujoco.mj_forward(model, data)
    plan = sahne.make_plan(data.xpos[model.body("kutu").id].copy())  # Kutunun yerine göre plan

    q = sahne.ready_pose(model, ghost, site, sahne.start_point(plan))  # İlk duruş
    duruslar = [("başla", q.copy(), sahne.GRIPPER_OPEN)]
    for ad, nokta, tutucu in plan:
        for _ in range(10):
            q = sahne.solve_ik(model, ghost, site, nokta, sahne.GRASP_ROT, q)  # Önceki duruştan başla
        ghost.qpos[:sahne.ARM_JOINTS] = q
        mujoco.mj_kinematics(model, ghost)
        hata = np.linalg.norm(ghost.site_xpos[site] - nokta) * 1000  # Ucun hedefe uzaklığı (mm)
        duruslar.append((ad, q.copy(), tutucu))
        print(f"// {ad:14s} hata {hata:.1f} mm")

    print("\nconst s16 DURUS[][6] = {                    // 2048 = orta, 4096 adım = bir tur")
    for ad, q, tutucu in duruslar:
        s = [adim(a) for a in q] + [adim(tutucu)]
        print(f"  {{{', '.join(str(v) for v in s)}}},     // {ad}")
    print("};")


if __name__ == "__main__":
    main()
