function setCord(map){
  var bounds = new google.maps.LatLngBounds();

  var areaCoords= [
    new google.maps.LatLng(51.526701598077565, -0.28429269790649414), // park royal
    new google.maps.LatLng(51.52966517664533, -0.2935624122619629), // hanger lane 
    new google.maps.LatLng(51.510602, -0.335402), // W7
    new google.maps.LatLng(51.464135, -0.265650), // SW14
    new google.maps.LatLng(51.42329633185242, -0.2614402770996094),
    new google.maps.LatLng(51.408434, -0.229908), // SW20
    new google.maps.LatLng(51.420395, -0.128057), // SW16
    new google.maps.LatLng(51.43944336078293, -0.10662317276000977), // tulse hill
    new google.maps.LatLng(51.462643882177574, -0.1137685775756836), // brixton
    new google.maps.LatLng(51.472256,-0.115797), // SW99
    new google.maps.LatLng(51.50119617280511, -0.12447595596313477), // westminter
    new google.maps.LatLng(51.5138304877587, -0.1502680778503418), // bond street
    new google.maps.LatLng(51.5134832912505, -0.15970945358276367), // marble arch
    new google.maps.LatLng(51.53372309742015, -0.20442724227905273) // queens park
  ];

  for (var i = 0; i < areaCoords.length; i++) {
    bounds.extend(areaCoords[i]);
  }
  map.setCenter(bounds.getCenter());
  map.fitBounds(bounds);

  areas_covered = new google.maps.Polygon({
    paths: areaCoords,
    strokeColor: '#00ADE0',
    strokeOpacity: 0.8,
    strokeWeight: 2,
    fillColor: '#00ADE0',
    fillOpacity: 0.35
  });

  areas_covered.setMap(map);
}

function initialize() {
    var mapOptions = {
      center: { lat: 51.484162350922226, lng: -0.19397735595703125},
      zoom: 12 
    };
    var map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);
    setCord(map);
}

google.maps.event.addDomListener(window, 'load', initialize);
