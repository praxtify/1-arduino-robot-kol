"""Ortak parçalar: SO101 sahnesi (kol + kutu + hedef bölge), ters kinematik ve al-bırak planı.

duruslar.py ve arduino_sim.py bu dosyayı içe aktarır; tek başına çalıştırılmaz.
"""
from pathlib import Path  # Dosya yolları

import mujoco  # Fizik motoru
import numpy as np  # Sayı dizileri ve matris hesapları

REPO = Path(__file__).resolve().parent.parent  # Repo kök klasörü
SCENE = REPO / "models/mujoco_menagerie/robotstudio_so101/scene.xml"  # Sadece robot kolu; kutuyu ve bölgeyi biz ekliyoruz

ARM_JOINTS = 5  # Kol motorları: ilk 5 motor (6. motor tutucu)
GRIPPER_OPEN = 0.6  # Tutucu açık (radyan, yaklaşık 6 cm aralık)
GRIPPER_CLOSED = -0.17  # Tutucu kapalı (en uç değer: motor kutuya dayanınca sıkmaya devam eder)

BOX_HALF = np.array([0.015, 0.015, 0.02])  # Kutunun yarı ölçüleri (m): 3 cm × 3 cm × 4 cm
BOX_START = np.array([0.22, 0.06, BOX_HALF[2]])  # Kutunun başlangıç yeri: robotun önünde, yerde
DROP_SPOT = np.array([0.16, -0.16])  # Hedef bölgenin merkezi (x, y)
HOVER = 0.05  # Kutunun üstünde ne kadar yukarıda dursun (5 cm)
GRASP_DEPTH = 0.012  # Çeneler kutunun ortasından bu kadar aşağıda kapansın (alt yarısından tutsun)

# Tutucunun istenen yönelimi: aşağı bak, çeneler y yönünde kapansın
GRASP_ROT = np.array([
    [0.0, -1.0, 0.0],
    [0.0, 0.0, 1.0],
    [-1.0, 0.0, 0.0],  # 1. sütun (0, 0, -1): tutucu aşağı bakıyor
])

# Ters kinematik ayarları
DAMPING = 0.02  # Yumuşatma payı (tekil duruşlarda sıçramayı önler)
ROT_WEIGHT = 0.3  # Yönelim hatası, konum hatasına göre ne kadar önemli
MAX_STEP = 0.05  # Bir hesap turunda en fazla dönüş (radyan)
IK_ITERATIONS = 30  # En fazla kaç tur hesap
IK_TOLERANCE = 0.0005  # 0,5 mm yakınlıkta hesabı bitir


def build_model():
    """Sahneye tutulacak kutuyu ve hedef bölgeyi ekle."""
    spec = mujoco.MjSpec.from_file(str(SCENE))  # Sahneyi düzenlenebilir hâlde aç
    box = spec.worldbody.add_body(name="kutu", pos=BOX_START.tolist())  # Kutu cismi
    box.add_freejoint()  # Serbest: düşebilir, itilebilir, tutulup kaldırılabilir
    box.add_geom(
        type=mujoco.mjtGeom.mjGEOM_BOX,  # Şekli: kutu
        size=BOX_HALF.tolist(),  # Yarı ölçüleri
        rgba=[0.1, 0.8, 0.2, 1],  # Yeşil
        mass=0.03,  # 30 gram
        friction=[1.5, 0.005, 0.0005],  # Kayma, dönme, yuvarlanma sürtünmesi (yüksek kayma → kaymadan tutulur)
        condim=6,  # Kayma + dönme sürtünmesi de hesaplansın
    )
    spec.worldbody.add_geom(  # Hedef bölge: yerde yarı saydam mavi kare (yalnız görsel)
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[DROP_SPOT[0], DROP_SPOT[1], 0.001],  # Yere yapışık
        size=[0.04, 0.04, 0.001],  # 8 cm × 8 cm
        rgba=[0.2, 0.4, 1, 0.5],
        contype=0,  # Hiçbir şeyle çarpışmasın
        conaffinity=0,
    )
    return spec.compile()  # Sahneyi fizik motoruna hazırla


def solve_ik(model, ghost, site_id, target_pos, target_rot, q_guess):
    """Ters kinematik (konum + yönelim): tutucu ucunu hedefe, istenen açıyla götüren eklem açılarını bul.

    Sönümlü en küçük kareler: her turda Jacobian ile küçük bir düzeltme hesaplanır, hayalet kol üzerinde denenir.
    """
    q = q_guess.copy()  # Önceki çözümden başla (kol sıçramasın)
    low = model.jnt_range[:ARM_JOINTS, 0]  # Eklemlerin en küçük açıları
    high = model.jnt_range[:ARM_JOINTS, 1]  # Eklemlerin en büyük açıları
    target_quat = np.zeros(4)
    mujoco.mju_mat2Quat(target_quat, target_rot.flatten())  # İstenen yönelim → kuaterniyon
    current_quat = np.zeros(4)
    rot_error = np.zeros(3)

    for _ in range(IK_ITERATIONS):
        ghost.qpos[:ARM_JOINTS] = q  # Hayalet kolu bu açılara getir
        mujoco.mj_kinematics(model, ghost)  # Parçaların konumlarını hesapla
        mujoco.mj_comPos(model, ghost)  # Jacobian için gereken ek bilgiler

        pos_error = target_pos - ghost.site_xpos[site_id]  # Konum farkı (m)
        current_rot = ghost.site_xmat[site_id].reshape(3, 3)  # Tutucunun şimdiki yönelimi
        mujoco.mju_mat2Quat(current_quat, ghost.site_xmat[site_id])
        mujoco.mju_subQuat(rot_error, target_quat, current_quat)  # Yönelim farkı (tutucunun kendi ekseninde)
        rot_error_world = current_rot @ rot_error  # Dünya eksenlerine çevir
        if np.linalg.norm(pos_error) < IK_TOLERANCE and np.linalg.norm(rot_error) < 0.01:
            break  # Hem yer hem yönelim tamam

        jac_pos = np.zeros((3, model.nv))  # Eklem dönünce uç ne kadar kayar
        jac_rot = np.zeros((3, model.nv))  # Eklem dönünce tutucu ne kadar döner
        mujoco.mj_jacSite(model, ghost, jac_pos, jac_rot, site_id)
        jac = np.vstack([jac_pos, ROT_WEIGHT * jac_rot])[:, :ARM_JOINTS]  # 6 × 5
        error = np.concatenate([pos_error, ROT_WEIGHT * rot_error_world])  # 6 sayı

        lhs = jac.T @ jac + DAMPING**2 * np.eye(ARM_JOINTS)
        dq = np.linalg.solve(lhs, jac.T @ error)  # Her eklemin dönüş miktarı
        biggest = np.max(np.abs(dq))
        if biggest > MAX_STEP:
            dq *= MAX_STEP / biggest  # Çok büyükse orantılı küçült
        q = np.clip(q + dq, low, high)  # Sınırların içinde tut
    return q


def ready_pose(model, ghost, site_id, point):
    """Başlangıç duruşu: tutucu aşağı bakarken uç verilen noktada olsun.

    Ters kinematik bazen yanlış bir duruşa takılır; birkaç başlangıç tahmini denenir, hedefe en yakını seçilir.
    """
    guesses = [np.zeros(ARM_JOINTS), np.array([0, -1, 1, 1, 0.0]), np.array([0, 0.5, 0.5, 1.5, 0.0])]
    best_q, best_err = None, np.inf
    for guess in guesses:
        q = guess
        for _ in range(10):
            q = solve_ik(model, ghost, site_id, point, GRASP_ROT, q)
        mujoco.mj_kinematics(model, ghost)
        err = np.linalg.norm(ghost.site_xpos[site_id] - point)
        if err < best_err:
            best_q, best_err = q, err
    return best_q


def make_plan(box_pos):
    """Al-bırak planı: her adım = (ad, tutucu ucunun gideceği nokta, tutucu komutu). Adlar .ino'daki yorumlarla aynı."""
    grasp = box_pos + np.array([0, 0, -GRASP_DEPTH])  # Tutma noktası: kutu merkezinin biraz altı
    above_box = grasp + np.array([0, 0, HOVER])  # Kutunun üstü
    drop_low = np.array([DROP_SPOT[0], DROP_SPOT[1], grasp[2] + 0.01])  # Bırakma noktası (yere çok yakın)
    above_drop = drop_low + np.array([0, 0, HOVER])  # Hedefin üstü
    return [
        ("kutunun üstü", above_box, GRIPPER_OPEN),
        ("aşağı in", grasp, GRIPPER_OPEN),
        ("kavra", grasp, GRIPPER_CLOSED),
        ("kaldır", above_box, GRIPPER_CLOSED),
        ("hedefin üstü", above_drop, GRIPPER_CLOSED),
        ("indir", drop_low, GRIPPER_CLOSED),
        ("bırak", drop_low, GRIPPER_OPEN),
        ("yukarı çekil", above_drop, GRIPPER_OPEN),
    ]


def start_point(plan):
    """Kolun başladığı nokta: kutunun üstünün 8 cm yanı (ilk adımda kutuya doğru hareket görünsün)."""
    p = plan[0][1].copy()
    p[1] -= 0.08
    return p
