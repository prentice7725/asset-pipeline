local sprite = app.activeSprite
assert(sprite, "No transparent game master PNG is open")

local params = app.params
local pixelLayer = sprite.layers[1]
assert(pixelLayer, "The transparent game master PNG has no layer")
pixelLayer.name = params.pixel_layer_name or "PIXEL_MASTER"

local backgroundPath = params.background_path
assert(backgroundPath and backgroundPath ~= "", "background_path is required")
local backgroundImage = Image{ fromFile=backgroundPath }
assert(backgroundImage, "Could not load the preserved background reference")
assert(backgroundImage.width == sprite.width and backgroundImage.height == sprite.height,
  "Background reference dimensions must match the native canvas")

local backgroundLayer = sprite:newLayer()
backgroundLayer.name = params.background_layer_name or "BACKGROUND_REFERENCE"
backgroundLayer.opacity = tonumber(params.background_opacity or "96")
backgroundLayer.isVisible = false
sprite:newCel(backgroundLayer, sprite.frames[1], backgroundImage, Point(0, 0))
