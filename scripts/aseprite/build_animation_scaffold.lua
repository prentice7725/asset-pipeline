local sprite = app.activeSprite
assert(sprite, "No transparent PIXEL_MASTER PNG is open")

local params = app.params
local pixelLayer = sprite.layers[1]
assert(pixelLayer, "The transparent master PNG has no pixel layer")
pixelLayer.name = params.pixel_layer_name or "PIXEL_ANIMATION"

local frameDurationMs = tonumber(params.frame_duration_ms or "90")
assert(frameDurationMs and frameDurationMs > 0, "frame_duration_ms must be positive")
local pivotX, pivotY = tonumber(params.pivot_x), tonumber(params.pivot_y)
assert(pivotX and pivotY, "pivot_x and pivot_y are required")
assert(pivotX >= 0 and pivotY >= 0 and pivotX < sprite.width and pivotY < sprite.height,
  "Pivot lies outside the native canvas")
local opacity = tonumber(params.reference_opacity or "128")
assert(opacity and opacity >= 0 and opacity <= 255, "reference_opacity must be between 0 and 255")

local referenceLayer = sprite:newLayer()
referenceLayer.name = params.reference_layer_name or "REFERENCE_WALK"
referenceLayer.opacity = opacity
referenceLayer.isVisible = true

local frameCount = 0
while params["reference_" .. (frameCount + 1)] do
  frameCount = frameCount + 1
end
assert(frameCount >= 6 and frameCount <= 8, "Walk scaffold needs 6–8 selected references")

local function addReference(frameIndex, frame)
  local imagePath = params["reference_" .. frameIndex]
  local image = Image{ fromFile=imagePath }
  assert(image, "Could not load selected reference: " .. imagePath)
  assert(image.width == sprite.width and image.height == sprite.height,
    "Reference images must be pre-aligned to the native canvas: " .. imagePath)
  sprite:newCel(referenceLayer, frame, image, Point(0, 0))
  frame.duration = frameDurationMs / 1000
end

sprite.frames[1].duration = frameDurationMs / 1000
addReference(1, sprite.frames[1])
for frameIndex = 2, frameCount do
  local frame = sprite:newEmptyFrame(frameIndex)
  local pixelImage = Image{ fromFile=params.pixel_png or "" }
  assert(pixelImage, "Could not load the static pixel master for a new animation slot")
  assert(pixelImage.width == sprite.width and pixelImage.height == sprite.height,
    "Static pixel master dimensions changed")
  sprite:newCel(pixelLayer, frame, pixelImage, Point(0, 0))
  frame.duration = frameDurationMs / 1000
  addReference(frameIndex, frame)
end

local tag = sprite:newTag(1, frameCount)
tag.name = params.tag_name or "walk"
tag.aniDir = AniDir.FORWARD

local slice = sprite:newSlice(Rectangle(0, 0, sprite.width, sprite.height))
slice.name = "character_pivot"
slice.pivot = Point(pivotX, pivotY)
