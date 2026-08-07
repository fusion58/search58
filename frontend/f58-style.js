/* Estilo de mapa base F58 (MapLibre) — tiles vectoriales OpenFreeMap.
   GeoServer WMTS no está configurado en GWC para QA; se usa el mismo
   style que OSRM (tiles.openfreemap.org/styles/liberty).

   Expone:
     window.F58Style.build()        -> URL del style MapLibre (OpenFreeMap liberty)
     window.F58Style.addIcons(map)  -> registra los iconos Maki para los POI
*/
(function () {
  var LIBERTY = 'https://tiles.openfreemap.org/styles/liberty';

  function build() { return LIBERTY; }

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
          for (var i = 0; i < def.d.length; i++) {
            try { ctx.fill(new Path2D(def.d[i])); } catch (e) {}
          }
        }
        if (!map.hasImage(name)) map.addImage(name, ctx.getImageData(0, 0, S, S));
      } catch (e) {}
    });
  }

  window.F58Style = { build: build, addIcons: addIcons };
})();
