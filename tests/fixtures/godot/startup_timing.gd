# Isolated 60Hz validation fixture, not a gameplay startup component.
extends SceneTree

var sprite: AnimatedSprite2D
var events: Array = []
var steps: Array = []
var started: int
var loops := 0
var guarded := false
var stable_count := 0
var previous_tick := 0
var armed_tick := 0
var readiness: Array = []
var rendered: Array = []

class Probe extends Node:
    var target
    func _process(delta: float) -> void:
        if target.guarded and target.started == 0:
            target.ready_step(delta)
        if target.started > 0:
            target.steps.append({"wall_ms":(Time.get_ticks_usec()-target.started)/1000.0,
                "delta_ms":delta*1000.0,"frame":target.sprite.frame})

func _initialize() -> void:
    if DisplayServer.get_name() != "headless":
        root.size=Vector2i(512,340)
        root.position=Vector2i(-12000,-12000)
    call_deferred("run_check")

func ready_step(delta: float) -> void:
    var tick := Time.get_ticks_usec()
    var wall_ms := (tick-previous_tick)/1000.0 if previous_tick > 0 else 0.0
    previous_tick=tick
    var ok: bool = delta >= 0.008 and delta <= 0.025 and wall_ms >= 8.0 and wall_ms <= 25.0 and abs(delta*1000.0-wall_ms) <= 4.0
    stable_count=stable_count+1 if ok else 0
    readiness.append({"wall_interval_ms":wall_ms,"delta_ms":delta*1000.0,"stable_count":stable_count})
    if stable_count >= 6:
        # Start after this process frame's animation updates, never in process_frame.
        sprite.stop()
        sprite.set_frame_and_progress(0,0.0)
        started=tick
        events.append({"frame":0,"wall_ms":0.0,"delta_ms":0.0})
        sprite.play("walk")
    elif tick-armed_tick > 2000000:
        push_error("STARTUP_NOT_STABLE: no animation started")
        quit(2)

func run_check() -> void:
    var mode := "guarded_none"
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--case="): mode = arg.trim_prefix("--case=")
    if mode not in ["export_two_frames","noexport_two_frames","slow_two_frames","export_warmup","slow_warmup","guarded_export","guarded_slow","guarded_none"]:
        push_error("Unknown diagnostic case")
        quit(2)
        return
    var frames: SpriteFrames = load("res://walk.tres")
    assert(frames.get_frame_count("walk") == 28)
    var load_start := Time.get_ticks_usec()
    if mode.contains("export"):
        DirAccess.make_dir_recursive_absolute("res://readback")
        for i in range(28):
            var image := frames.get_frame_texture("walk",i).get_image()
            assert(image.save_png("res://readback/%02d.png" % i)==OK)
    if mode.contains("slow"):
        OS.delay_msec(250)
    var load_ms := (Time.get_ticks_usec()-load_start)/1000.0
    sprite=AnimatedSprite2D.new()
    sprite.sprite_frames=frames
    sprite.centered=false
    sprite.offset=Vector2(-256,-510)
    sprite.position=Vector2(256,300)
    root.add_child(sprite)
    var probe=Probe.new()
    probe.target=self
    root.add_child(probe)
    sprite.frame_changed.connect(func(): events.append({"frame":sprite.frame,
        "wall_ms":(Time.get_ticks_usec()-started)/1000.0,
        "delta_ms":sprite.get_process_delta_time()*1000.0}))
    sprite.animation_looped.connect(func(): loops+=1)
    if DisplayServer.get_name() != "headless":
        RenderingServer.frame_post_draw.connect(func():
            if started > 0:
                rendered.append({"frame":sprite.frame,"wall_ms":(Time.get_ticks_usec()-started)/1000.0}))
    await process_frame
    await process_frame
    if mode.ends_with("warmup"):
        var warm_started := Time.get_ticks_usec()
        while Time.get_ticks_usec()-warm_started < 500000:
            await process_frame
    if mode.begins_with("guarded"):
        armed_tick=Time.get_ticks_usec()
        guarded=true
        while started == 0:
            await process_frame
    else:
        sprite.stop()
        sprite.set_frame_and_progress(0,0.0)
        started=Time.get_ticks_usec()
        events.append({"frame":0,"wall_ms":0.0,"delta_ms":0.0})
        sprite.play("walk")
    while Time.get_ticks_usec()-started < 4000000:
        await process_frame
    var settings={}
    for field in ProjectSettings.get_property_list():
        var key: String=field["name"]
        if key.contains("delta_smoothing") or key.contains("max_fps") or key.contains("vsync_mode"):
            settings[key]=ProjectSettings.get_setting(key)
    var output={"case":mode,"load_work_ms":load_ms,"events":events,"steps":steps,
        "engine":Engine.get_version_info(),"settings":settings,"loops":loops,
        "time_scale":Engine.time_scale,"fps":24,"frame_count":28,
        "display_server":DisplayServer.get_name(),"rendered_frames":rendered.duplicate(true),"readiness":readiness,
        "readiness_wait_ms":(started-armed_tick)/1000.0 if guarded else 0.0,"game_ready":false}
    var suffix := "-"+DisplayServer.get_name().to_lower()
    FileAccess.open("res://timing-%s%s.json" % [mode,suffix],FileAccess.WRITE).store_string(JSON.stringify(output,"  "))
    if DisplayServer.get_name() != "headless":
        sprite.pause()
        await RenderingServer.frame_post_draw
        var image:=root.get_texture().get_image()
        assert(image.save_png("res://timing-%s%s.png" % [mode,suffix])==OK)
    print("TIMING_DIAGNOSTIC_COMPLETE ",mode," loops=",loops)
    quit(0)

