local sprite = app.activeSprite
assert(sprite, "No base Aseprite animation master is open")

local params = app.params
local pixelLayerName = params.pixel_layer_name or "PIXEL_ANIMATION"
local pixelLayer = nil
for _, layer in ipairs(sprite.layers) do
  if layer.name == pixelLayerName then
    pixelLayer = layer
    break
  end
end
assert(pixelLayer, "Base master is missing " .. pixelLayerName)

local frameCount = tonumber(params.frame_count or "8")
assert(frameCount == #sprite.frames, "Frame count does not match the preserved base master")
for index = 1, frameCount do
  local imagePath = params["frame_" .. index]
  assert(imagePath, "Missing edited frame PNG for frame " .. index)
  local image = Image{ fromFile=imagePath }
  assert(image, "Could not load edited pixel frame " .. imagePath)
  assert(image.width == sprite.width and image.height == sprite.height,
    "Edited frame dimensions do not match the Aseprite canvas: " .. imagePath)

  local existing = nil
  for _, cel in ipairs(pixelLayer.cels) do
    if cel.frame == sprite.frames[index] then
      existing = cel
      break
    end
  end
  if existing then
    existing.image = image
    existing.position = Point(0, 0)
    existing.opacity = 255
  else
    sprite:newCel(pixelLayer, sprite.frames[index], image, Point(0, 0))
  end
end

assert(sprite.width == 160 and sprite.height == 160, "Phase 11 requires the 160x160 native canvas")
assert(sprite.tags[1] and sprite.tags[1].name == "walk", "The preserved walk tag is missing")
