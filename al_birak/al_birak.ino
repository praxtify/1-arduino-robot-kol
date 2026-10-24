#include <SCServo.h>                        // Feetech servo kütüphanesi

SMS_STS servo;                              // STS3215 seri bus servolar

u8  ID[6]   = {1, 2, 3, 4, 5, 6};           // taban, omuz, dirsek, bilek, dönüş, tutucu
u16 HIZ[6]  = {800, 800, 800, 800, 800, 800};  // adım / saniye
u8  IVME[6] = {40, 40, 40, 40, 40, 40};     // × 100 adım / saniye²

const s16 DURUS[][6] = {                    // 2048 = orta, 4096 adım = bir tur
  {2161, 1996, 2192, 2980, 3217, 2439},     // başla
  {1879, 2014, 2171, 2982, 2934, 2439},     // kutunun üstü
  {1878, 2093, 2327, 2748, 2934, 2439},     // aşağı in
  {1878, 2093, 2327, 2748, 2934, 1937},     // kavra
  {1878, 2016, 2170, 2983, 2934, 1937},     // kaldır
  {2672, 2148, 1956, 3064, 3728, 1937},     // hedefin üstü
  {2672, 2192, 2140, 2837, 3728, 1937},     // indir
  {2672, 2192, 2140, 2837, 3728, 2439},     // bırak
  {2672, 2148, 1956, 3064, 3728, 2439},     // yukarı çekil
};
const int ADIM = sizeof(DURUS) / sizeof(DURUS[0]);

void git(const s16 durus[6]) {
  s16 hedef[6];
  for (int j = 0; j < 6; j++) hedef[j] = durus[j];
  servo.SyncWritePosEx(ID, 6, hedef, HIZ, IVME);  // altı servo, tek paket
  delay(20);
  for (int j = 0; j < 6; j++)
    while (servo.ReadMove(ID[j]) == 1) delay(10);  // hepsi varana kadar bekle
}

void setup() {
  Serial1.begin(1000000);                   // D0 / D1 → Waveshare UART
  servo.pSerial = &Serial1;
  delay(1000);
  for (int i = 0; i < ADIM; i++) {
    git(DURUS[i]);
    delay(300);                             // tutucu otursun
  }
}

void loop() {}
