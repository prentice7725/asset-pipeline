local sprite = app.activeSprite
assert(sprite, "No sprite was opened from the source PNG")

local params = app.params
local firstLayer = sprite.layers[1]
assert(firstLayer, "The imported PNG did not create a pixel layer")
firstLayer.name = params.layer_name or "Pixel"

local durationMs = tonumber(params.frame_duration_ms or "100")
assert(durationMs and durationMs > 0, "frame_duration_ms must be a positive number")

local frameIndex = 2
while params["frame_" .. frameIndex] do
  local framePath = params["frame_" .. frameIndex]
  local image = Image{ fromFile=framePath }
  assert(image, "Could not load additional frame: " .. framePath)
  assert(image.width == sprite.width and image.height == sprite.height,
    "Additional frame dimensions must match the master canvas: " .. framePath)
  local frame = sprite:newEmptyFrame(frameIndex)
  sprite:newCel(firstLayer, frame, image, Point(0, 0))
  frame.duration = durationMs / 1000
  frameIndex = frameIndex + 1
end

for _, frame in ipairs(sprite.frames) do
  frame.duration = durationMs / 1000
end

local tag = sprite:newTag(1, #sprite.frames)
tag.name = params.tag_name or "static"
tag.aniDir = AniDir.FORWARD

if params.pivot_x or params.pivot_y then
  local x = tonumber(params.pivot_x)
  local y = tonumber(params.pivot_y)
  assert(x and y, "pivot_x and pivot_y must both be integers")
  assert(x >= 0 and y >= 0 and x < sprite.width and y < sprite.height,
    "Pivot lies outside the sprite canvas")
  local slice = sprite:newSlice(Rectangle(0, 0, sprite.width, sprite.height))
  slice.name = "character_pivot"
  slice.pivot = Point(x, y)
end
