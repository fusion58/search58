/* Estilo de mapa base F58 (MapLibre) desde el GeoServer propio (tiles MVT).
   Portado de mapa_vectorial.html. La URL del WMTS va por el proxy /geoserver/
   del mismo origen (nginx) para evitar CORS.

   Expone:
     window.F58Style.build()        -> objeto de estilo MapLibre (version 8)
     window.F58Style.addIcons(map)  -> registra los iconos Maki para los POI
*/
(function () {
  // Tiles MVT del GeoServer, vía proxy nginx (mismo origen).
  // URL ABSOLUTA (location.origin): MapLibre no fetchea tiles con URL relativa.
  var F58_MVT = window.location.origin + '/geoserver/gwc/service/wmts'
    + '?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0'
    + '&LAYER=F58-Map:F58-Map&STYLE='
    + '&TILEMATRIX=EPSG:900913:{z}&TILEMATRIXSET=EPSG:900913'
    + '&FORMAT=application/vnd.mapbox-vector-tile'
    + '&TILECOL={x}&TILEROW={y}';

  var SRC = 'f58';
  var HEIGHT_FACTOR = 800000;

  var BUILDING_TIERS = [
    { id: 'bldg-1', minzoom: 14, maxzoom: 16, area: 0.8 },
    { id: 'bldg-2', minzoom: 16, maxzoom: 17, area: 0.30 },
    { id: 'bldg-3', minzoom: 17, maxzoom: 18, area: 0.13 },
    { id: 'bldg-4', minzoom: 18, maxzoom: 19, area: 0.05 },
    { id: 'bldg-5', minzoom: 19, maxzoom: 21, area: 0 }
  ];
  var BUILDING_PAINT = {
    'fill-extrusion-color': '#ece7df',
    'fill-extrusion-height': ['max', 4, ['*', ['coalesce', ['get', 'height_random'], 0], HEIGHT_FACTOR]],
    'fill-extrusion-base': 0,
    'fill-extrusion-opacity': 0.6
  };

  var ZW = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
  var CENTER_W = {
    motorway: [1.5, 1.8, 3, 3, 4, 7, 13, 20, 35, 54],
    motorway_link: [1.3, 1.5, 3, 3, 3, 6, 9, 14, 28, 46],
    main: [1.3, 1.5, 3, 3, 3, 6, 9, 14, 28, 46],
    primary: [1.3, 1.5, 3, 3, 3, 6, 9, 14, 28, 46],
    secondary: [0.2, 0.2, 1, 1.5, 3, 5, 6, 10, 21, 38],
    street: [0.4, 0.4, 0.4, 0.4, 2.5, 3, 4, 6, 15, 30],
    service: [0.2, 0.2, 0.3, 0.4, 1.5, 2, 2.5, 4, 9, 18],
    _def: [0.4, 0.4, 0.4, 0.4, 2.5, 3, 4, 6, 15, 30]
  };
  var CASING_W = {
    motorway: [0.2, 0.2, 0.2, 5, 7, 11, 17, 24, 39, 58],
    motorway_link: [0.2, 0.2, 0.2, 4, 5, 9, 12, 17, 31, 49],
    main: [0.2, 0.2, 0.2, 4, 5, 9, 12, 17, 31, 49],
    primary: [0.2, 0.2, 0.2, 4, 5, 9, 12, 17, 31, 49],
    secondary: [0.2, 0.2, 0.2, 3, 4, 8, 9, 13, 24, 41],
    street: [0.2, 0.2, 0.2, 0.2, 4, 5, 6, 8, 17, 32],
    service: [0.2, 0.2, 0.2, 0.2, 3, 3.5, 4, 5, 12, 22],
    _def: [0.2, 0.2, 0.2, 0.2, 4, 5, 6, 8, 17, 32]
  };
  var ROAD_CLASSES = ['motorway', 'motorway_link', 'main', 'primary', 'secondary', 'street', 'service'];
  function widthExpr(table) {
    var e = ['interpolate', ['linear'], ['zoom']];
    ZW.forEach(function (z, i) {
      var m = ['match', ['get', 'class_way']];
      for (var k = 0; k < ROAD_CLASSES.length; k++) { var c = ROAD_CLASSES[k]; m.push(c, table[c][i]); }
      m.push(table._def[i]);
      e.push(z, m);
    });
    return e;
  }
  var roadWidth = widthExpr(CENTER_W);
  var casingWidth = widthExpr(CASING_W);

  var centerColor = ['match', ['get', 'type'],
    'tertiary', '#ffffff',
    'tertiary_link', '#ffffff',
    'residential', '#ffffff',
    ['match', ['get', 'class_way'],
      'motorway', '#f4bd80', 'motorway_link', '#f4dd8a', 'main', '#fce988',
      'primary', '#fce988', 'secondary', '#f3ecd8', 'service', '#eeeeee', '#f3ecd8']
  ];

  var poiIcon = ['match', ['get', 'type'],
    ['restaurant', 'fast_food', 'food_court', 'food_beverages', 'ice_cream', 'farm'], 'restaurant',
    ['cafe', 'coffee'], 'cafe', ['bar', 'pub'], 'bar',
    ['hospital', 'clinic', 'doctors', 'dentist'], 'hospital',
    ['pharmacy', 'chemist'], 'pharmacy', 'fuel', 'fuel',
    ['station', 'bus_station'], 'bus', 'subway', 'rail-metro',
    ['school', 'university', 'college', 'kindergarten', 'library'], 'school',
    'bank', 'bank',
    ['supermarket', 'convenience', 'grocery', 'kiosk', 'general', 'greengrocer'], 'grocery',
    ['clothes', 'clothing', 'shoes'], 'clothing-store',
    ['mall', 'shop', 'toys', 'pet', 'do-it-yourself', 'photo', 'car', 'hardware'], 'shop',
    ['place_of_worship', 'church'], 'place-of-worship',
    ['hotel', 'lodging', 'guest_house'], 'lodging', 'beach', 'beach',
    ['peak', 'mountain', 'viewpoint'], 'mountain', 'parking', 'parking', 'marker'];
  var poiTypes = ['restaurant', 'fast_food', 'food_court', 'food_beverages', 'ice_cream', 'farm', 'cafe', 'coffee', 'bar', 'pub', 'hospital', 'clinic', 'doctors', 'dentist', 'pharmacy', 'chemist', 'fuel', 'station', 'bus_station', 'subway', 'school', 'university', 'college', 'kindergarten', 'library', 'bank', 'supermarket', 'convenience', 'grocery', 'kiosk', 'general', 'greengrocer', 'clothes', 'clothing', 'shoes', 'mall', 'shop', 'toys', 'pet', 'do-it-yourself', 'photo', 'car', 'hardware', 'place_of_worship', 'church', 'hotel', 'lodging', 'guest_house', 'beach', 'peak', 'mountain', 'viewpoint', 'parking'];
  var poiPrio = ['match', ['get', 'type'],
    ['hospital', 'clinic', 'doctors', 'dentist', 'fuel', 'bank', 'station', 'bus_station', 'subway', 'school', 'university', 'college', 'place_of_worship', 'church', 'mall'], 1,
    ['restaurant', 'fast_food', 'food_court', 'food_beverages', 'ice_cream', 'cafe', 'coffee', 'bar', 'pub', 'shop', 'clothes', 'clothing', 'toys', 'pet'], 3, 2];

  function L(id, type, sourceLayer, extra) {
    var o = { id: id, type: type, source: SRC, 'source-layer': sourceLayer };
    for (var k in extra) o[k] = extra[k];
    return o;
  }

  function build() {
    var layers = [
      { id: 'fondo', type: 'background', paint: { 'background-color': '#e8ebed' } },
      L('batimetria', 'fill', 'F58-Batimetria', { paint: { 'fill-color': '#bcd9f0' } }),
      L('tierra', 'fill', 'F58-Tierra', { paint: { 'fill-color': '#f8f4f0' } }),
      L('green', 'fill', 'F58-Green-Fija', { paint: { 'fill-color': '#b3dd8a' } }),
      L('aero-area', 'fill', 'F58-Aeropuertos-Area', { paint: { 'fill-color': '#dadcd0' } }),
      L('landuse', 'fill', 'F58-Landuse', { paint: {
        'fill-color': ['match', ['get', 'type'],
          ['park', 'theme_park', 'garden', 'grass', 'pitch', 'sport', 'sports_center', 'cemetery', 'recreation_ground', 'meadow', 'village_green', 'allotments', 'dog_park', 'playground', 'golf_course', 'nature_reserve', 'scrub', 'heath'], '#b3dd8a',
          ['forest', 'wood'], '#a6d57b', '#e9e7d8'],
        'fill-opacity': 0.6 } }),
      L('variosarea', 'fill', 'F58-VariosArea', { paint: { 'fill-color': '#dedbd4', 'fill-opacity': 0.6 } }),
      L('water-pol', 'fill', 'F58-Water-Pol', { paint: { 'fill-color': '#bbdaf2' } }),
      L('water-lin', 'line', 'F58-Water-Lin', { paint: { 'line-color': '#bbdaf2', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.6, 17, 4] } }),
      L('limite-costa', 'line', 'F58-Limite-Costa', { paint: { 'line-color': '#a0c8f0', 'line-width': 1 } }),
      L('limites', 'line', 'F58-Limites', { paint: { 'line-color': '#c2b2cc', 'line-width': 1.2, 'line-dasharray': [3, 2] } }),
      L('roads-casing', 'line', 'F58-Vias', { minzoom: 10, filter: ['!=', ['get', 'class_rail'], 'subway'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#d8cdb8', 'line-width': casingWidth } }),
      L('roads-center', 'line', 'F58-Vias', { minzoom: 10, filter: ['!=', ['get', 'class_rail'], 'subway'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': centerColor, 'line-width': roadWidth } }),
      L('subway', 'line', 'F58-Vias', { minzoom: 11, filter: ['==', ['get', 'class_rail'], 'subway'], paint: { 'line-color': '#bdbdbd', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 1, 18, 3] } }),
      L('tuneles', 'line', 'F58-Tuneles', { minzoom: 12, layout: { 'line-cap': 'butt' }, paint: { 'line-color': '#fcf1e0', 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 1, 18, 8], 'line-dasharray': [3, 1.5] } }),
      L('puentes-casing', 'line', 'F58-Puentes', { minzoom: 11, layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#d8cdb8', 'line-width': casingWidth } }),
      L('puentes-center', 'line', 'F58-Puentes', { minzoom: 11, layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': centerColor, 'line-width': roadWidth } }),
      L('aero-pista', 'line', 'F58-Aeropuertos-Pista', { minzoom: 11, paint: { 'line-color': '#c2c2c2', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 1.5, 17, 14] } })
    ];
    BUILDING_TIERS.forEach(function (t) {
      var f = ['all', ['has', 'name'], ['!=', ['get', 'name'], '']];
      if (t.area > 0) f.push(['>=', ['coalesce', ['get', 'area'], 0], t.area]);
      layers.push(L(t.id, 'fill-extrusion', 'F58-Building', { minzoom: t.minzoom, maxzoom: t.maxzoom, filter: f, paint: BUILDING_PAINT }));
    });
    layers.push(
      L('lbl-place', 'symbol', 'F58-Place', { minzoom: 8, layout: { 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 8, 11, 14, 16], 'text-anchor': 'center' }, paint: { 'text-color': '#444444', 'text-halo-color': '#ffffff', 'text-halo-width': 1.4 } }),
      L('lbl-vias', 'symbol', 'F58-Vias', { minzoom: 14, filter: ['all', ['has', 'name'], ['!=', ['get', 'name'], '']], layout: { 'symbol-placement': 'line', 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': 11 }, paint: { 'text-color': '#5e5e5a', 'text-halo-color': '#ffffff', 'text-halo-width': 1.3 } }),
      L('poi-icon', 'symbol', 'F58-POI', { minzoom: 14, filter: ['in', ['get', 'type'], ['literal', poiTypes]], layout: { 'icon-image': poiIcon, 'icon-size': ['interpolate', ['linear'], ['zoom'], 14, 0.24, 16, 0.42, 18, 0.72], 'icon-padding': ['interpolate', ['linear'], ['zoom'], 14, 2, 16, 7, 18, 16], 'icon-allow-overlap': false, 'symbol-sort-key': poiPrio, 'text-field': ['step', ['zoom'], '', 16, ['get', 'name']], 'text-font': ['Noto Sans Regular'], 'text-size': 10, 'text-anchor': 'top', 'text-offset': [0, 0.9], 'text-optional': true }, paint: { 'text-color': '#3a3a38', 'text-halo-color': '#ffffff', 'text-halo-width': 1.3 } }),
      L('lbl-water', 'symbol', 'F58-Water-Pol-Name', { minzoom: 12, filter: ['all', ['has', 'name'], ['!=', ['get', 'name'], '']], layout: { 'symbol-placement': 'line', 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': 11 }, paint: { 'text-color': '#458fdf', 'text-halo-color': '#ffffff', 'text-halo-width': 1.2 } })
    );

    return {
      version: 8,
      glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      sources: {},  // la fuente 'f58' se agrega abajo para poder setear tiles dinámicos
      layers: layers,
      // fuente declarada aparte para claridad
      _f58src: true
    };
  }

  // Devuelve el estilo con la fuente vector incluida
  function buildFull() {
    var s = build();
    s.sources[SRC] = { type: 'vector', tiles: [F58_MVT], minzoom: 0, maxzoom: 19 };
    delete s._f58src;
    return s;
  }

  // Registra los iconos Maki (mismos del raster) como imágenes del mapa
  function addIcons(map) {
    if (!window.MAKI_ICONS) return;
    var S = 44;
    Object.keys(window.MAKI_ICONS).forEach(function (name) {
      var def = window.MAKI_ICONS[name];
      try {
        var cv = document.createElement('canvas'); cv.width = S; cv.height = S;
        var ctx = cv.getContext('2d');
        ctx.scale(S / 20, S / 20);
        ctx.beginPath(); ctx.arc(10, 10, 9, 0, 2 * Math.PI);
        ctx.fillStyle = def.color; ctx.fill();
        ctx.lineWidth = 1; ctx.strokeStyle = '#ffffff'; ctx.stroke();
        if (def.d && def.d.length) {
          ctx.translate(def.tx, def.ty); ctx.scale(def.s, def.s);
          ctx.fillStyle = '#ffffff';
          for (var i = 0; i < def.d.length; i++) { try { ctx.fill(new Path2D(def.d[i])); } catch (e) {} }
        }
        if (!map.hasImage(name)) map.addImage(name, ctx.getImageData(0, 0, S, S));
      } catch (e) {}
    });
  }

  window.F58Style = { build: buildFull, addIcons: addIcons };
})();
