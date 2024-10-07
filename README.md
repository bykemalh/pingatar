# PingATAR

PingATAR, ağ yöneticileri ve sistem administratörleri için geliştirilmiş, çoklu IP adreslerini eş zamanlı olarak ping atıp sonuçlarını görsel bir arayüzde sunan güçlü bir ağ izleme aracıdır.

## Özellikler

- Çoklu IP adreslerine eş zamanlı ping atma
- Ping sonuçlarını gerçek zamanlı olarak görüntüleme
- IP adresleri için MAC adresi bulma
- Başarısız ping durumlarında e-posta bildirimi
- Kullanıcı dostu grafiksel arayüz
- Windows ve Linux işletim sistemleri ile uyumlu

## Geliştirici

PingATAR, Kemal Hafızoğlu tarafından geliştirilmiştir. Daha fazla bilgi için [bykemalh.me](https://www.bykemalh.me) adresini ziyaret edebilirsiniz.

## Kurulum

### Windows

1. En son sürümü [Releases](https://github.com/bykemalh/pingatar/releases) sayfasından indirin.
2. İndirilen .exe dosyasını çalıştırın.

### Linux

1. En son sürümü [Releases](https://github.com/bykemalh/pingatar/releases) sayfasından indirin.
2. İndirilen .AppImage dosyasını çalıştırılabilir yapın:
   ```
   chmod +x PingATAR-x.x.x.AppImage
   ```
3. AppImage'i çalıştırın:
   ```
   ./PingATAR-x.x.x.AppImage
   ```

## Kullanım

1. Uygulamayı başlatın.
2. "Edit IP" butonuna tıklayarak veya Edit menüsünden "Edit IP" seçeneğini seçerek IP adreslerini ekleyin/düzenleyin.
3. "Start" butonuna tıklayarak ping işlemini başlatın.
4. Sonuçları ana ekranda görüntüleyin.

## Katkıda Bulunma

1. Bu projeyi fork edin.
2. Yeni bir branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Bir Pull Request oluşturun.

## Lisans

Bu proje GNU General Public License v3.0 altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## İletişim

Kemal Hafızoğlu - [@bykemalh](https://twitter.com/bykemalh) - info@bykemalh.me

Proje Linki: [https://github.com/bykemalh/pingatar](https://github.com/bykemalh/pingatar)


Bu README dosyası, PingATAR uygulamasının temel özelliklerini, kurulum talimatlarını, kullanım bilgilerini ve diğer önemli detayları içermektedir. Windows ve Linux için kurulum talimatları eklenmiştir. 

MacOS için özel bir paket olmadığından ve AppImage'in MacOS'te çalışıp çalışmadığından emin olmadığımız için, MacOS için özel bir bölüm eklemedim. Eğer MacOS kullanıcıları uygulamayı kullanmak isterlerse, kaynak kodu indirip derleyebilirler.
