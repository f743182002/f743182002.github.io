// 陣列順序同時用於完整相簿、分類、精選列及燈箱。
window.PHOTOS = [
  {
    "source": "635685_去浮水印.jpg",
    "file": "living-wide.jpg",
    "rooms": [
      "living",
      "dining"
    ],
    "title": "客廳",
    "caption": "客廳與餐廳相連，左側可見窗戶與通往陽台的門。"
  },
  {
    "source": "635688_0.jpg",
    "file": "living.jpg",
    "rooms": [
      "living"
    ],
    "title": "客廳",
    "caption": "客廳可見黑框窗、淺色牆面與地板。"
  },
  {
    "source": "635687_去浮水印.jpg",
    "file": "living-balcony-door.jpg",
    "rooms": [
      "living"
    ],
    "title": "客廳",
    "caption": "客廳前方的窗戶旁有通往陽台的門。"
  },
  {
    "source": "635684_去浮水印.jpg",
    "file": "living-dining-front.jpg",
    "rooms": [
      "living",
      "dining"
    ],
    "title": "客餐廳",
    "caption": "客餐廳地板相連，右側可見房門與開口。"
  },
  {
    "source": "635689_去浮水印.jpg",
    "file": "living-dining-wide.jpg",
    "rooms": [
      "living",
      "dining"
    ],
    "title": "客餐廳",
    "caption": "客廳連接餐廳，右側門口可看見後方窗戶。"
  },
  {
    "source": "635686_0.jpg",
    "file": "living-dining.jpg",
    "rooms": [
      "living",
      "dining"
    ],
    "title": "客餐廳",
    "caption": "客廳與餐廳相連，餐廳旁可見房門及通道。"
  },
  {
    "source": "635673_0.jpg",
    "file": "room-bed-a.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房間設有黑框窗，牆面與地板皆為淺色。"
  },
  {
    "source": "635674_0.jpg",
    "file": "room-bed-b.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房門外可見相連通道與另一處窗戶。"
  },
  {
    "source": "635675_0.jpg",
    "file": "room-ottoman-a.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房間牆面設有黑框窗，下方可見淺色地板。"
  },
  {
    "source": "635676_0.jpg",
    "file": "room-ottoman-b.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房間右側設有窗戶，牆角與地板交界清楚可見。"
  },
  {
    "source": "635678_0.jpg",
    "file": "room-table-a.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房間前方設有黑框窗，兩側為淺色牆面。"
  },
  {
    "source": "635679_0.jpg",
    "file": "room-table-b.jpg",
    "rooms": [
      "bedroom"
    ],
    "title": "房間",
    "caption": "房間左側設有窗戶，右側可見房門。"
  },
  {
    "source": "635680_0.jpg",
    "file": "kitchen.jpg",
    "rooms": [
      "kitchen"
    ],
    "title": "廚房",
    "caption": "廚房兩側為磁磚牆面，後端設有黑框窗。"
  },
  {
    "source": "635682_0.jpg",
    "file": "kitchen-end.jpg",
    "rooms": [
      "kitchen"
    ],
    "title": "廚房",
    "caption": "廚房窗戶左側有通往陽台的門，周圍為磁磚牆面。"
  },
  {
    "source": "635683_去浮水印.jpg",
    "file": "kitchen-reverse.jpg",
    "rooms": [
      "kitchen"
    ],
    "title": "廚房",
    "caption": "廚房兩側磁磚牆面之間的通道連接前方門口。"
  },
  {
    "source": "635681_0.jpg",
    "file": "balcony-upper.jpg",
    "rooms": [
      "balcony"
    ],
    "title": "陽台",
    "caption": "陽台鋪有磁磚地板，一側是門窗，另一側是欄板。"
  },
  {
    "source": "635690_去浮水印.jpg",
    "file": "balcony-street.jpg",
    "rooms": [
      "balcony"
    ],
    "title": "陽台",
    "caption": "長形陽台鋪有磁磚，兩側可見欄板、玻璃欄片與門窗。"
  },
  {
    "source": "635672_0.jpg",
    "file": "bathroom-a.jpg",
    "rooms": [
      "bathroom"
    ],
    "title": "衛浴",
    "caption": "衛浴牆面與地板鋪有磁磚，淋浴區地面設有高低落差。"
  },
  {
    "source": "635677_0.jpg",
    "file": "bathroom-b.jpg",
    "rooms": [
      "bathroom"
    ],
    "title": "衛浴",
    "caption": "衛浴可見磁磚牆面與地板，淋浴區旁有地面排水孔。"
  }
];
window.PhotoLibrary = {
  groups: [['all','全部'],['living','客廳'],['dining','餐廳'],['bedroom','房間'],['kitchen','廚房'],['balcony','陽台'],['bathroom','衛浴']],
  categoryForRoom(id) {
    return ({bedroom1:'bedroom',bedroom2:'bedroom',bedroom3:'bedroom',bathroom1:'bathroom',bathroom2:'bathroom',balcony1:'balcony',balcony2:'balcony'})[id] || id;
  },
  filter(id) {
    return id==='all' ? window.PHOTOS : window.PHOTOS.filter(photo=>photo.rooms.includes(id));
  },
  forRoom(id) {
    return this.filter(this.categoryForRoom(id));
  },
  featured(files) {
    return window.PHOTOS.filter(photo=>files.includes(photo.file));
  }
};
