# Nasdaq Telegram alarmı — deneysel sürüm

Bu paket hazır bir bulut kurulumu değildir. İşlem açmaz. PC kapalıyken ancak
GitHub Actions veya başka bir sunucuya kurulursa çalışır. Ücretsiz denemede
yaklaşık 5 dakikalık kontrol amaçlanır; GitHub tetiklemeleri gecikebilir veya
atlanabilir. Saniyelik kırılım takibi için uygun değildir.

## Neler var?

- Nasdaq (NMS/NGM/NCM) aday keşfi; 0,20–20 dolar. FRGT örneği nedeniyle
  alt sınır 1 dolar değil 0,20 olarak ayarlanmıştır; config.json ile değişir.
- En çok 20 aday. Liste keşfi normal seans verisine dayanabilir: tüm Nasdaq
  premarket taraması değildir. watchlist alanına ek semboller yazılabilir.
- Seans hacmi en az 100.000 ve önceki kapanışa göre en az %5 yükseliş.
- Seanslar ayrı; ABD saat dilimi/yaz saati, işlem günleri ve erken kapanış
  takvimle kontrol edilir. Tatil takvimi XNYS kullanılır; Nasdaq'a özel
  beklenmedik kapanışlar ayrıca doğrulanmalıdır.
- Tamamlanmış 1 dakikalık mumlarda iki sol ve iki sağ mumla teyit edilmiş
  en son yerel tepe giriş seviyesi olur. İlk 8 mumdan önce alarm yoktur.
  Bu, incelenen kişinin bütün giriş kurallarını kopyaladığı iddiası değildir.
- %3 yaklaşma; tamamlanmış mum kapanışı seviyeyi aşınca kırılım alarmı.
  Fitilin anlık aşılması ayrı izlenmez. Kontroller arasındaki kırılımlar kaçabilir.
- R1/R2 girişin üstündeki teyitli geçmiş tepelerden seçilir; yakın seviyeler
  birleştirilir. Son 6 aylık günlük veri kullanılır; bölünmeler düzeltilir.
  Geçmiş gün içi tepeler bu ilk sürümde R1/R2 taramasına dahil değildir.
- Stop adayı, giriş tepesinden sonraki tamamlanmış geri çekilmenin en düşük
  fiyatıdır. Stop bir emir değildir; gerçekleşme garantisi yoktur.
- Son 24 saat haber başlığı, saati ve bağlantısı. FDA onayı / kotasyon şartlarına
  uyum gibi başlık ifadeleri olumlu ipucu; halka arz / ters bölünme gibi ifadeler
  olumsuz ipucu olarak etiketlenir. Çakışmada KARIŞIK, eşleşme yoksa BELİRSİZ.
  Başlık eşleşmesi tam haber metni değerlendirmesi değildir; yanıltıcı başlıklarda
  yanlış sınıflanabilir. Tam metin ve güvenilir sınıflandırma tamamlanmamıştır.
- 180 saniyeden eski mumlarda alarm verilmez. Aynı gün/seans/seviye/tür
  için tekrar engellenir. Bulut önbelleği silinirse tekrar mesaj gelebilir.

## Ücretsiz kurulum

1. https://github.com/signup adresinden hesap oluştur.
2. Boş bir **public** repository aç: örneğin nasdaq-alert-bot.
   Public depo kodu herkese gösterir. Token/chat ID asla dosyalara yazılmaz.
   Actions fiyat/limitlerini hesabında kontrol et; ücretli kullanım açma.
3. Bu klasörün içeriğini depo köküne yükle. Gizli .github klasörü ve
   .github/workflows/scan.yml dosyası da dahil olmalı.
4. BotFather ile sohbette paylaşılmış tokenı iptal edip yenisini al.
5. Repository > Settings > Secrets and variables > Actions bölümünde
   TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID adlı iki secret ekle.
   Chat ID'yi güvenli yerel bağlantı testiyle bulabiliriz; public dosyaya koyma.
6. Actions > Deneysel Nasdaq alarmi > Run workflow ile elle test et.
7. İlk olarak logları ve Telegram mesajlarını grafikle karşılaştır.
   Piyasa dışındaysa alarm üretmez. İşlem günü ve veri kalitesi ayrıca test edilmelidir.

## Yerel doğrulama

Python 3.12+:

```text
pip install -r requirements.txt
python -m unittest -v
python bot.py --dry-run
```

Gerçek mesaj gönderimi için TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ortam
değişkenleri gerekir. --dry-run mesaj göndermez ve tekrar durumunu değiştirmez.

## Sınırlar ve kaynaklar

Yahoo/yfinance resmî bir borsa veri hizmeti değildir; kesilebilir, kısıtlanabilir
veya gecikebilir. Kütüphane kişisel kullanım koşullarını ayrıca incele:
https://github.com/ranaroussi/yfinance

GitHub zamanlayıcı sınırları:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

Bu pakette canlı veri taraması, bulut kurulumu ve tam metin haber duygu analizi
tamamlanmış/garanti edilmiş değildir. Otomatik testler alarm matematiğini kontrol
eder; stratejinin kârlı olduğunu kanıtlamaz.
