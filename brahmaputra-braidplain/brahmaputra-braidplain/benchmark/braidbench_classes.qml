<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  Class colours for the braided river benchmark.
  Load onto any label raster: right-click layer > Properties > Style > Load Style.

  Using the same colours for every annotator and every figure means a reader
  learns the palette once. Do not change these between tiles or between people.
-->
<qgis version="3.34" styleCategories="Symbology">
  <pipe>
    <rasterrenderer type="paletted" band="1" opacity="1" alphaBand="-1" nodataColor="">
      <rasterTransparency/>
      <colorPalette>
        <paletteEntry value="0" color="#2b2b2b" alpha="255" label="0 background"/>
        <paletteEntry value="1" color="#2b7bba" alpha="255" label="1 water"/>
        <paletteEntry value="2" color="#e8d4a0" alpha="255" label="2 bare bar"/>
        <paletteEntry value="3" color="#4a8a3f" alpha="255" label="3 vegetated bar"/>
        <paletteEntry value="255" color="#c0392b" alpha="255" label="255 uncertain"/>
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation saturation="0" colorizeOn="0"/>
  </pipe>
</qgis>
