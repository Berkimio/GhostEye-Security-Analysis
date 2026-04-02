# 🛡️ GhostEye: Siber Güvenlik Analizi ve Bilgi Sızdırma Mekanizmaları

**GhostEye**, modern bilgi hırsızlığı yazılımlarının (infostealers) teknik altyapısını, veri toplama metodolojilerini ve uzak komuta kontrol (C2) sistemleriyle haberleşme biçimlerini incelemek amacıyla geliştirilmiş **eğitim tabanlı bir güvenlik araştırması** projesidir.

---

### ⚠️ YASAL UYARI (IMPORTANT LEGAL DISCLAIMER)
Bu proje sadece siber güvenlik eğitimi, etik hackleme çalışmaları ve savunma mekanizmalarının geliştirilmesi amacıyla hazırlanmıştır. Bu kodun veya türevlerinin yetkisiz sistemlerde kullanılması **YASAL SUÇTUR**. Yazılımın kötüye kullanımından doğabilecek tüm sorumluluk kullanıcıya aittir.

---

## 🔍 Proje Amacı ve Kapsamı
Bu çalışma, bir saldırganın sistem üzerinde nasıl kalıcılık sağladığını ve kritik verileri (şifreler, tarayıcı verileri, sistem bilgileri) nasıl ayıkladığını anlamak isteyen güvenlik profesyonelleri için bir laboratuvar ortamı sunar.



## ⚙️ Teknik Özellikler ve Analiz Edilen Alanlar

### 1. Sistem Analizi ve Sandbox Tespiti
Kod, analiz edilmesini zorlaştırmak için şu teknikleri kullanır:
* **VM Check:** MAC adresi ve sistem sürücüleri (`VBoxMouse.sys`, `vm3dmp.sys`) üzerinden sanal makine tespiti.
* **Privilege Check:** Yazılımın yönetici (Admin) haklarına sahip olup olmadığını denetleme.

### 2. Kalıcılık (Persistence)
* **Windows Registry:** `Software\Microsoft\Windows\CurrentVersion\Run` anahtarı kullanılarak başlangıçta otomatik çalışma simülasyonu.
* **Stealth Mode:** `ctypes` kütüphanesi ile konsol penceresini gizleyerek arka planda çalışma.

### 3. Veri Toplama ve Sızdırma (Exfiltration)
* **Browser Data:** Chrome ve Edge tabanlı tarayıcıların SQLite veritabanlarını (`Login Data`, `Cookies`, `History`) yedekleme.
* **Network Discovery:** `netsh` komutları ile kayıtlı Wi-Fi profillerini ve açık şifreleri toplama.
* **Sensitive File Scan:** Regex (Düzenli İfadeler) kullanarak `.env`, `.py`, `.sql` gibi dosyalarda API anahtarları ve şifre kalıplarını arama.
* **Screen Capture:** `pyautogui` ile anlık ekran görüntüsü alma.

### 4. Komuta Kontrol (C2) - Telegram Entegrasyonu
Telegram Bot API üzerinden şu interaktif komutlar yönetilebilir:
- `/sysinfo`: Detaylı donanım ve IP bilgisi.
- `/cmd`: Uzaktan komut satırı (Command Prompt) erişimi.
- `/download`: Sistemden dosya çekme.
- `/upload`: Uzaktan sisteme dosya yükleme ve çalıştırma.
- `XXX`: **Self-Destruct** (Tüm izleri ve kendini silerek sistemden ayrılma).

## 🛡️ Savunma ve Önleme Stratejileri
Bu projeyi analiz eden bir uzman şu defansif çıkarımları yapabilir:
1. **Registry Monitoring:** Kayıt defterindeki otomatik başlatma anahtarlarının EDR/Antivirüs ile izlenmesi.
2. **Network Filtering:** Bilinmeyen uygulamaların `api.telegram.org` üzerinden veri transferi yapmasının engellenmesi.
3. **Behavioral Analysis:** Arka planda çalışan gizli Python süreçlerinin ve ani dosya tarama aktivitelerinin tespiti.

## 🚀 Kurulum (Sanal Laboratuvar İçin)

1. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install requests pyautogui

    Kodun başındaki TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID alanlarını kendi test botunuzla doldurun.

    DİKKAT: Bu işlemi sadece kendi kontrolünüzdeki bir sanal makinede (VM) gerçekleştirin.

📄 Lisans

Bu proje MIT License ile lisanslanmıştır.
