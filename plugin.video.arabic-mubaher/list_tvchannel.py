

class list_tv:
    def fill():
       
        # ,{"name":"channel ","kind":"p","country":"ps" ,"url":"url1","logo":"logo1"},
        satellite_channel="القناة الفضائية" 
        news_channel="قناة الاخبارية"
        Documentary="قناة الوثائقية"
        kids_channel="قناة الاطفال"
        drama_channel="قناة استعراض"
        classic_channel="قناة عرض قديمة "
        flim_channel="شريط عرض"
        channels=[

             {"name":"قناة فلسطين مباشر ","kind":satellite_channel,"country":"فلسطين" ,"url":"https://pbc.furrera.ps/palestinelivehd/index.m3u8","logo":"https://safa.ps/thumb/w1000/uploads/images/2022/11/HjpzP.png"},
             {"name":"قناة هلا ","kind":satellite_channel,"country":"فلسطين " ,"url":"https://live2.panet.co.il/edge_abr/halaTV/edge_abr/halaTV_1080p/chunks.m3u8","logo":"http://psce.pw/4vchfx"},
             {"name":"قناة الأردن ","kind":satellite_channel,"country":"الأردن" ,"url":"https://jrtv-live.ercdn.net/jordanhd/jordanhd.m3u8","logo":"http://psce.pw/4w6j8n"},
             {"name":"قناة القدس يوم   ","kind":satellite_channel,"country":"فلسطين" ,"url":"http://live.alqudstoday.tv:8080/hls/alqudstv/alqudstv.m3u8","logo":"https://is.gd/mYHff2"},
             {"name":"قناة سوريا ","kind":satellite_channel,"country":"سوريا" ,"url":"https://svs.itworkscdn.net/syriatvlive/syriatv.smil/playlist_dvr.m3u8","logo":"http://psce.pw/4w6j3k"},
            
            
            
             {"name":" قناة رؤيا درما","kind":satellite_channel,"country":"الأردن" ,"url":"https://tinyurl.com/25wxkxda","logo":"https://cdn01.paltoday.ps/ar/thumb/940x610/uploads/images/2022/05/h7DgM.jpg"},
           
             {"name":" قناة رؤيا كوميدي","kind":satellite_channel,"country":"الأردن" ,"url":"https://tinyurl.com/2cfmuras","logo":"https://cdn01.paltoday.ps/ar/thumb/940x610/uploads/images/2022/05/h7DgM.jpg"},

           
             {"name":"قناة الميادين  ","kind":satellite_channel,"country":"لبنان" ,"url":"https://mdnlv.cdn.octivid.com/almdn/smil:mpegts.stream.smil/chunklist_b3000000_t64NTQwcA==.m3u8","logo":"https://media.almayadeen.tv/uploads/archive/default.png"},
              {"name":"سكاي نيوز عربية ","kind":news_channel,"country":"الإمارات" ,"url":"https://stream.skynewsarabia.com/hls/sna.m3u8","logo":"https://m.eyeofriyadh.com/news_images/2020/01/1c376f37a51aa.jpg"},
              {"name":"الجزيرة ","kind":news_channel,"country":"ps" ,"url":"https://live-hls-web-aja.getaj.net/AJA/index.m3u8","logo":"https://pbs.twimg.com/ext_tw_video_thumb/1458689463547219968/pu/img/gE8Cs-DTUNnqt0cy.jpg:large"},
              
              {"name":"National Geographic Abu Dhabi ","kind":Documentary,"country":"الإمارات" ,"url":"https://admdn2.cdn.mangomolo.com/nagtv/smil:nagtv.stream.smil/playlist.m3u8","logo":"https://is.gd/8sJYfo"},
              
              {"name":"DW arabic ","kind":Documentary,"country":"المانيا" ,"url":"https://dwamdstream103.akamaized.net/hls/live/2015526/dwstream103/index.m3u8","logo":"https://is.gd/tfmz91"},
              {"name":"MBC1 ","kind":satellite_channel,"country":"الحجاز" ,"url":"https://is.gd/F8P5sh","logo":"https://is.gd/t3bwtL"},
              {"name":"MBC2","kind":satellite_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/2q6zer6h","logo":"https://tinyurl.com/y6c5rjeu"},
              {"name":"MBC 3  ","kind":kids_channel,"country":"الحجاز" ,"url":"https://is.gd/45ldkw","logo":"https://is.gd/u7tHjm"},
              {"name":"MBC 4 ","kind":satellite_channel,"country":"الحجاز" ,"url":"https://is.gd/SRRwnB","logo":"https://is.gd/7VeRA2"},
              {"name":"MBC 5  ","kind":satellite_channel,"country":"الحجاز" ,"url":"https://is.gd/OIrcH0","logo":"https://is.gd/MrqWOO"},
              {"name":"MBC Plus Drama  ","kind":drama_channel,"country":"الحجاز" ,"url":"https://is.gd/dNo23x","logo":"https://is.gd/f0eYGI"},
              {"name":"MBC Masr 1","kind":satellite_channel,"country":"مصر" ,"url":"https://is.gd/zxFFxs","logo":"https://is.gd/pfaX9I"},
              {"name":"MBC Masr 2","kind":satellite_channel,"country":"مصر" ,"url":"https://is.gd/510JqZ","logo":"https://is.gd/a2pbJY"},
              {"name":"العربي","kind":news_channel,"country":"البريطانيا" ,"url":"https://tinyurl.com/22pzd7sb","logo":"https://is.gd/KA9aeM"},
              {"name":"المنار ","kind": satellite_channel,"country":"لبنان" ,"url":"https://is.gd/pK8no5","logo":"https://is.gd/pQTm9I"},
              {"name":"الاقصى  ","kind":"satellite_channel","country":"فلسطين" ,"url":"https://tinyurl.com/2po6q2al","logo":"https://tinyurl.com/2zyl24gk"},
              {"name":"دبي 1 ","kind":satellite_channel,"country":"الإمارات" ,"url":"https://is.gd/ZTkf25","logo":"https://is.gd/9l4hKr"},
              {"name":"دبي ","kind":satellite_channel,"country":"الإمارات" ,"url":"https://is.gd/1HgOTB","logo":"https://is.gd/S5i701"},
              {"name":"سورية ","kind":satellite_channel,"country":"سوريا","url":"https://is.gd/8okSEe","logo":"https://is.gd/zdOVZc"},
              {"name":" سورية دراما ","kind":drama_channel,"country":"سوريا" ,"url":"https://is.gd/nRy9gq","logo":"https://is.gd/DbUBmU"},
              {"name":"قناة سما   ","kind":satellite_channel,"country":"سوريا" ,"url":"https://tinyurl.com/2dyvrpf2","logo":"https://is.gd/YA3Vyf"},
              { "name":" روتانا كلاسيك" ,"kind":classic_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/4vfbjckt","logo":"https://tinyurl.com/2nn6frpp"},
              {"name":"قناة المملكة  ","kind":satellite_channel,"country":"الأردن" ,"url":"https://tinyurl.com/mr4862wa","logo":"https://tinyurl.com/7feyzdku"},
              {"name":"روتانا سنيما ","kind":flim_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/2afjv38k","logo":"https://tinyurl.com/4ky9nht7"},
              {"name":" روتانا سنيما 2","kind":flim_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/58hezv9m","logo":"https://tinyurl.com/3z9wcm69"},
              {"name":"روتانا الاطفال","kind":kids_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/2tyymsvd","logo":"https://tinyurl.com/2p8zjcte"},
              {"name":"روتانا+ ","kind":flim_channel,"country":"الحجاز" ,"url":"https://tinyurl.com/2p9unfue","logo":"https://tinyurl.com/c3ejutab"},
              {"name":"Spacetoon","kind":kids_channel,"country":"سوريا + الإمارات" ,"url":"https://tinyurl.com/26tj935t","logo":"https://tinyurl.com/44u2y94y"},


                           #{"name":"channel ","kind":"p","country":"ps" ,"url":"url1","logo":"logo1"},


              ]
        return channels
