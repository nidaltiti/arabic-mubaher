

class list_tv:
    def fill():
       
        # ,{"name":"channel ","kind":"p","country":"ps" ,"url":"url1","logo":"logo1"},
        satellite_channel="القناة الفضائية" 
        news_channel="قناة الاخبارية"
        Documentary="قناة الوثائقية"
        channels=[

            {"name":"قناة فلسطين مباشر ","kind":satellite_channel,"country":"فلسطين" ,"url":"https://pbc.furrera.ps/palestinelivehd/index.m3u8","logo":"https://safa.ps/thumb/w1000/uploads/images/2022/11/HjpzP.png"},
            {"name":"قناة هلا ","kind":satellite_channel,"country":"فلسطين " ,"url":"https://live2.panet.co.il/edge_abr/halaTV/edge_abr/halaTV_1080p/chunks.m3u8","logo":"http://psce.pw/4vchfx"},
            {"name":"قناة الأردن ","kind":satellite_channel,"country":"الأردن" ,"url":"https://jrtv-live.ercdn.net/jordanhd/jordanhd.m3u8","logo":"http://psce.pw/4w6j8n"},
            {"name":"قناة القدس يوم   ","kind":satellite_channel,"country":"فلسطين" ,"url":"http://live.alqudstoday.tv:8080/hls/alqudstv/alqudstv.m3u8","logo":"https://is.gd/mYHff2"},
             {"name":"قناة سوريا ","kind":satellite_channel,"country":"سوريا" ,"url":"https://svs.itworkscdn.net/syriatvlive/syriatv.smil/playlist_dvr.m3u8","logo":"http://psce.pw/4w6j3k"},
             {"name":"قناة رؤيا ","kind":satellite_channel,"country":"الأردن" ,"url":"https://roya.daioncdn.net/royatv/royatv.m3u8?app=8c1e143a-39cf-40b4-acb2-e78faa1f322d&ce=3","logo":"https://cdn01.paltoday.ps/ar/thumb/940x610/uploads/images/2022/05/h7DgM.jpg"},
             {"name":"قناة الميادين  ","kind":satellite_channel,"country":"لبنان" ,"url":"https://mdnlv.cdn.octivid.com/almdn/smil:mpegts.stream.smil/chunklist_b3000000_t64NTQwcA==.m3u8","logo":"https://media.almayadeen.tv/uploads/archive/default.png"},
              {"name":"سكاي نيوز عربية ","kind":news_channel,"country":"الإمارات" ,"url":"https://stream.skynewsarabia.com/hls/sna.m3u8","logo":"https://m.eyeofriyadh.com/news_images/2020/01/1c376f37a51aa.jpg"},
              {"name":"الجزيرة ","kind":news_channel,"country":"ps" ,"url":"https://live-hls-web-aja.getaj.net/AJA/index.m3u8","logo":"https://pbs.twimg.com/ext_tw_video_thumb/1458689463547219968/pu/img/gE8Cs-DTUNnqt0cy.jpg:large"},
              
              {"name":"National Geographic Abu Dhabi ","kind":Documentary,"country":"الإمارات" ,"url":"https://admdn2.cdn.mangomolo.com/nagtv/smil:nagtv.stream.smil/playlist.m3u8","logo":"https://is.gd/8sJYfo"},
              
              {"name":"DW arabic ","kind":Documentary,"country":"المانيا" ,"url":"https://dwamdstream103.akamaized.net/hls/live/2015526/dwstream103/index.m3u8","logo":"https://is.gd/tfmz91"},
       
              
              ]
        return channels
