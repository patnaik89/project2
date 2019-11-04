import maya.mel
import maya.cmds

import random


# constants to tweak

autoplay = False
autostop = True
bake = True

layers = 6

timeline_frames_per_turn = 150
timeline_extra_frames = 300

frame_set = 1#0=quick, 1=default, 2=slow

frames_before_starting = 30
rotation_frames = [2, 15, 120][frame_set]
lineup_frames = [2, 10, 120][frame_set]
rearing_frames = [2, 10, 120][frame_set]
hitting_frames = 8
returning_frames = 10
frames_before_checking = [10, 40, 120][frame_set]
frames_between_checks = 10
frames_before_ending = 180

#physics
table_dynamic_friction = 1.0
table_static_friction = 1.0
table_bounciness = 0.0
table_mass = 1.0
table_damping = 2.0

block_dynamic_friction = 0.2
block_static_friction = 0.4
block_bounciness = 0.0
block_mass = 100.0
block_damping = 2.0
block_center_of_mass = (0.0, 0.0, 0.0)

player_dynamic_friction = 0.2
player_static_friction = 0.2
player_bounciness = 0.6
player_mass = 1.0
player_damping = 0.0


#positions and sizes
offset_y = 1
block_fell_if_below = offset_y - 1

block_scale = 2.0
block_w = block_scale * 2.5
block_h = block_scale * 1.5
block_d = block_scale * 7.5

spacing = block_scale * 0.02
height_gap = block_h + spacing
width_gap = block_w + spacing

player_size = block_scale * 0.4
player_resting_height = offset_y + (2*block_h)
player_resting_distance_from_tower = block_d * 1.33
player_furthest_distance_to_tower = player_resting_distance_from_tower * 1.2
player_closest_distance_to_tower = block_d * 0.5 + player_size/2

table_radius = block_d * 0.9
table_thickness = table_radius * 0.15


gravity_magnitude = 40 * block_scale


#debugging
print_player_positions = False
state_block_visible = False
testText = False



#Functions for preparing the scene:

def prepareMaterial(material_name, r, g, b):
    if not maya.cmds.objExists(material_name):
        maya.cmds.shadingNode("blinn", asShader=True, name=material_name)
        maya.cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=material_name+"SG")
        maya.cmds.connectAttr(material_name+".outColor", material_name+"SG.surfaceShader", f=True)
        maya.cmds.setAttr(material_name+".color", r, g, b, type="double3")

def deleteObjects(deletestring):
    matching_objects = maya.cmds.ls(deletestring)
    if len(matching_objects):
        maya.cmds.delete(matching_objects)

def deleteOldObjects():
    to_delete = ["Block*", "Table", "gravityField*", "PState", "p1g", "p2g", "p2gg", "runPython", "Text*", "cam*", "Order*"]
    for thing in to_delete:
        deleteObjects(thing)

def recordOrder():
    order = []
    for i in range(layers):
        #choose which blocks they will try to remove
        if random.getrandbits(1) or i==3:
            order.extend([(i*3)+1, (i*3)+3])
        else:
            order.append((i*3)+2)

    #shuffle the order they are removed
    random.shuffle(order)

    #export the order so it persists
    for i in range(len(order)):
         sname="Order{}".format(i+1)
         maya.cmds.polyCube(w=1, h=1, d=1, name=sname)
         maya.cmds.move(order[i], -10, 0, sname)
         maya.cmds.setAttr("Order{}.visibility".format(i+1), 0)


def makeTable():
    table = maya.cmds.polyCylinder(r=table_radius, h=table_thickness, name="Table")
    maya.cmds.move(0, offset_y - ((table_thickness+block_h)/2) - spacing, 0, table)
    maya.cmds.rigidBody(active=0, passive=1, dynamicFriction=table_dynamic_friction, staticFriction=table_static_friction, bounciness=table_bounciness, mass=table_mass, damping=table_damping)
    maya.cmds.defaultNavigation(source="table_color", destination="|Table|TableShape.instObjGroups[0]", connectToExisting=1)
    maya.cmds.polyBevel3("Table", fraction=0.1, offsetAsFraction=1, autoFit=1, segments=5, worldSpace=1, smoothingAngle=30, fillNgons=1, mergeVertices=1, mergeVertexTolerance=0.0001, miteringAngle=180, angleTolerance=180, ch=1)
    return table

def makeBlock(layer, side):
    block = maya.cmds.polyCube(w=block_w, h=block_h, d=block_d, name="Block#")

    if layer%2:
        maya.cmds.rotate(0, 90, 0, block, r=1)
        block_move_x = 0
        block_move_z = (side-1) * width_gap
    else:
        block_move_x = (side-1) * width_gap
        block_move_z = 0
    maya.cmds.move(block_move_x, offset_y + (layer*height_gap), block_move_z, block)

    maya.cmds.rigidBody(bounciness=block_bounciness, staticFriction=block_static_friction, dynamicFriction=block_dynamic_friction, mass=block_mass, damping=block_damping, centerOfMass=block_center_of_mass)
    number = side + 1 + (3*layer)
    maya.cmds.defaultNavigation(source="block_color", destination="|Block{}|Block{}Shape.instObjGroups[0]".format(number, number), connectToExisting=1)
    maya.cmds.polyBevel3("Block{}".format(number), fraction=0.1, offsetAsFraction=1, autoFit=1, segments=5, worldSpace=1, smoothingAngle=30, fillNgons=1, mergeVertices=1, mergeVertexTolerance=0.0001, miteringAngle=180, angleTolerance=180, ch=1)
    return block

def makePlayer(number):
    pname = "p{}".format(int(number))
    maya.cmds.polySphere(name=pname)#gotta group it and recenter that.
    maya.cmds.scale(player_size, player_size, player_size, pname)
    maya.cmds.move(player_resting_distance_from_tower, player_resting_height, 0, pname)
    maya.cmds.rigidBody(active=0, passive=1, bounciness=player_bounciness, staticFriction=player_static_friction, dynamicFriction=player_dynamic_friction, mass=player_mass, damping=player_damping)
    maya.cmds.group(pname, n=pname+"g")
    maya.cmds.move(0, 0, 0, pname+"g.scalePivot", pname+"g.rotatePivot")

def makeText(name, content, visible):
    #
    maya.mel.eval("typeCreateText")
    maya.cmds.rename("typeMesh1", name)
    maya.cmds.rename("type1", name+"base")
    maya.cmds.rename("typeExtrude1", name+"extrude")
    maya.cmds.setAttr(name+'base.currentFont', 'Consolas', type='string')
    maya.cmds.setAttr(name+'base.fontSize', 1)
    maya.cmds.setAttr(name+'extrude.extrudeDistance', 0.1)
    maya.cmds.move(0,0,0, name)
    maya.cmds.setAttr(name+'base.textInput', content, type='string')
    #maya.cmds.textCurves(f="Helvetica|wt:50|sz:280|sl:n|st:100", t=content, n=name)
    maya.cmds.setAttr(name+".visibility", int(visible))


def resetScene():
    deleteOldObjects()
    random.seed()

    prepareMaterial("block_color", 1, 1, 0)#yellow
    prepareMaterial("table_color", 1, 1, 1)#white

    #also change winning text if you change the player colors
    prepareMaterial("player_1_color", 0, 0, 1)#blue
    prepareMaterial("player_2_color", 1, 0, 0)#red

    recordOrder()

    total_turns = len(set(maya.cmds.ls("Order*", o=1)) - set(maya.cmds.ls("Order*Shape", o=1)))

    total_timeline_frames = (timeline_frames_per_turn * total_turns) + timeline_extra_frames

    maya.cmds.currentTime(1)
    maya.cmds.playbackOptions(animationEndTime=total_timeline_frames, maxTime=total_timeline_frames)


    grav = maya.cmds.gravity(m=gravity_magnitude)

    for layer in range(layers):
        for side in range(3):
            makeBlock(layer, side)

    blockList = maya.cmds.ls("Block*", o=1)

    makeTable()

    makePlayer(1)
    makePlayer(2)

    maya.cmds.group("p2g", n="p2gg")
    maya.cmds.move(0, 0, 0, "p2gg.scalePivot", "p2gg.rotatePivot", a=1)
    maya.cmds.rotate(0, 180, 0, "p2gg")
    maya.cmds.defaultNavigation(source="player_1_color", destination="|p1g|p1|p1Shape.instObjGroups[0]", connectToExisting=1)
    maya.cmds.defaultNavigation(source="player_2_color", destination="|p2gg|p2g|p2|p2Shape.instObjGroups[0]", connectToExisting=1)

    maya.cmds.polyCube(w=1, h=1, d=1, name="PState")
    maya.cmds.move(1, 0, frames_before_starting, "PState")#1 is turn, 0 is phase
    maya.cmds.scale(1, layers, 1, "PState")#that first 1 is overall frame number; last 1 is (winner+1)
    maya.cmds.setAttr("PState.visibility", int(state_block_visible))

    maya.cmds.polyCube(w=1, h=1, d=1, name="baked")
    maya.cmds.setAttr("baked.visibility", 0)

    makeText("TextP1Win", "Blue Wins!", False)
    makeText("TextP2Win", "Red Wins!", False)
    makeText("TextTie", "Tie!", testText)

    maya.cmds.move(0, 0, 0, "persp")
    maya.cmds.setAttr("persp.rotateX", 0)
    maya.cmds.setAttr("persp.rotateY", 0)
    maya.cmds.setAttr("persp.rotateZ", 0)
    maya.cmds.camera()
    maya.cmds.rename("camera1", "render_camera")
    maya.cmds.group("render_camera", "persp", n="cameras")

    maya.cmds.group("TextP1WinShape", "TextP2WinShape", "TextTieShape", n="text")
    maya.cmds.move(-5, 2, -10, "text")

    maya.cmds.group("cameras", "text", n="camera_and_text")

    maya.cmds.move(0, 2*block_scale, 30*block_scale, "camera_and_text")

    maya.cmds.group("camera_and_text", n="camera_group")
    maya.cmds.move(0, 0, 0, "camera_group.scalePivot", "camera_group.rotatePivot", a=1)
    maya.cmds.rotate(-30, -30, 0, "camera_group")

    maya.cmds.setAttr("render_cameraShape.renderable", 1)
    maya.cmds.setAttr("persp.renderable", 0)

    maya.cmds.currentTime(1)

    maya.cmds.connectDynamic(blockList, fields=grav[0])

    return total_timeline_frames


def runEveryFrame():

    if not maya.cmds.ls("baked", o=1):
        return

    def get_block_location(name):
        return maya.cmds.xform(name, q=1, t=1, ws=1)

    def get_block_scale(name):
        return maya.cmds.xform(name, q=1, s=1, ws=1)

    psxft = get_block_location("PState")
    psxfs = get_block_scale("PState")
    turn = int(psxft[0])
    phase = int(-psxft[1])
    frames_left = int(psxft[2])
    layers = int(psxfs[1])
    overall_frame_number = int(psxfs[0])
    winner = int(psxfs[2]) - 1

    def set_winner(winner):
	#set others to 0 every turn for keyframing purposes.
        maya.cmds.setAttr("TextP1Win.visibility", 0)
        maya.cmds.setAttr("TextP2Win.visibility", 0)
        maya.cmds.setAttr("TextTie.visibility", 0)
        if winner:
            if winner == 1:
                maya.cmds.setAttr("TextP1Win.visibility", 1)
            elif winner == 2:
                maya.cmds.setAttr("TextP2Win.visibility", 1)
            elif winner == 3:
                maya.cmds.setAttr("TextTie.visibility", 1)

    def next_block():
        try:
            return int(get_block_location("Order{}".format(turn))[0])
        except:
            return 0

    def need_rotate():
        return ((next_block()+2)//3)%2

    def next_block_name():
        return "Block{}".format(int(next_block()))

    def next_block_side():
        return ((next_block()-1)%3)-1

    def player():
        return int((turn%2)+1)

    def player_name():
        return "p{}".format(player())

    def player_group_name():
        return "p{}g".format(player())

    def player_sign():
        if player()==1:
            return 1
        return -1

    def block_fell(block):
        return get_block_location(block)[1] < block_fell_if_below

    def get_blocks():
        return list(set(maya.cmds.ls("Block*", o=1)) - set(maya.cmds.ls("Block*Shape", o=1)))

    def rotate_player(degrees):
        if need_rotate():
            maya.cmds.rotate(0, degrees, 0, player_group_name(), r=1)

    def move_towards(x, y, z):
        #make one frame of progress towards a location
        new_x, new_y, new_z = get_block_location(player_name())[:3]
        if x is not None:
            new_x += (x-new_x)/frames_left
        if y is not None:
            new_y += (y-new_y)/frames_left
        if z is not None:
            new_z += (z-new_z)/frames_left
        maya.cmds.move(new_x, new_y, new_z, player_name())

    def change_distance_from_tower(distance):
        if need_rotate():
            move_towards(None, None, player_sign() * -distance)
        else:
            move_towards(player_sign() * distance, None, None)


    """
    Phases:
        0: pre-action. do nothing so blocks can settle
        1: rotate to correct position
        2: move into vertical position and line up with the correct row
        3: rear back
        4: hit block
        5: move back to original distance away (position at end of phase 2)
        6: rotate back to neutral
        7: move back to neutral
        8: delay before block-checking starts
        9: wait for a block to fall, and check that only one fell
        10: wait before ending
        11: end video
        12: video already over; loop forever
    """

    #next_phase = [1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 11, 12, 12]#below is clearer
    next_phase = {0:1, 1:2, 2:3, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9, 9:9, 10:11, 11:12, 12:12}
    phase_frames = {1:rotation_frames, 2:lineup_frames, 3:rearing_frames, 4:hitting_frames, 5:returning_frames,
                    6:rotation_frames, 7:lineup_frames, 8:frames_before_checking, 9:frames_between_checks, 10:frames_before_ending, 11:1, 12:1}

    if not frames_left:
        phase = next_phase[phase]
        frames_left = phase_frames[phase]

    #now run the next frame of the phase
    if phase==1:#rotate to correct position
        rotate_player(90.0/phase_frames[phase])
    elif phase==2:#move into vertical position and line up with the correct row
        block_y = get_block_location(next_block_name())[1]
        x_or_z = next_block_side() * width_gap
        if need_rotate():
            move_towards(x_or_z, block_y, None)
        else:
            move_towards(None, block_y, x_or_z)
    elif phase==3:#rear back
        change_distance_from_tower(player_furthest_distance_to_tower)
    elif phase==4:#hit block
        change_distance_from_tower(player_closest_distance_to_tower)
    elif phase==5:#move back to original distance away
        change_distance_from_tower(player_resting_distance_from_tower)
    elif phase==6:#rotate back to neutral
        rotate_player(-90.0/phase_frames[phase])
    elif phase==7:#move back to neutral
        move_towards(None, player_resting_height, 0)
    elif phase==9:#wait for a block to fall, and check that only one fell
        if frames_left == 1:
            remaining = len([block for block in get_blocks() if not block_fell(block)])
            expected_remaining = len(get_blocks()) - turn
            if remaining == expected_remaining:
                #only one fell
                turn += 1
                if next_block():
                    #take next turn
                    phase = 1
                else:
                    #no turns left, tie
                    phase = 10
                    winner = 3
            elif remaining < expected_remaining:
                #multiple fell; someone wins
                phase = 10
                winner = (player()%2)+1#current turn is loser's.
            else:
                #none have fallen yet; wait longer
                pass
            frames_left = phase_frames[phase]+1#add one because it will be decremented at the end of this frame.
    elif phase==11:#end video
        if autostop:
            maya.cmds.play(state=False)
        maya.cmds.setAttr("defaultRenderGlobals.endFrame", overall_frame_number)

    set_winner(winner)

    print("FRAME: {} {} {} {}".format(turn, phase, frames_left, next_block_name()))

    if print_player_positions:
        print("P1: X: {}, Y: {}, Z: {}".format(*get_block_location("p1")[:3]))
        print("P2: X: {}, Y: {}, Z: {}".format(*get_block_location("p2")[:3]))

    #store important information so that it can be retrieved next frame
    maya.cmds.move(turn, -phase, frames_left-1, "PState")
    maya.cmds.scale(overall_frame_number+1, layers, winner+1, "PState")

total_timeline_frames = resetScene()

maya.cmds.expression(n='runPython', s='python(\"runEveryFrame()\")')

if bake:
    things_to_bake = list(set(maya.cmds.ls("Block*", o=1)) - set(maya.cmds.ls("Block*Shape", o=1))) + ["Table", "p1", "p2", "p2g", "p2gg", "p1g", "PState", "TextP1Win", "TextP2Win", "TextTie"]
    maya.cmds.bakeResults(*things_to_bake, attribute=["tx", "ty", "tz", "rx", "ry", "rz", "v"], simulation=True, t=(1,total_timeline_frames), sampleBy=1, disableImplicitControl=True, preserveOutsideKeys=False, sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False, removeBakedAnimFromLayer=False, bakeOnOverrideLayer=False, minimizeRotation=True, controlPoints=False, shape=True)
    for i in range((layers*3) + 3):
        maya.cmds.setAttr("rigidBody{}.active".format(i+1), 0)
    deleteObjects("baked")
elif autoplay:
    maya.cmds.play()

maya.cmds.setAttr("defaultRenderQuality.enableRaytracing", 1)
maya.cmds.setAttr("defaultRenderGlobals.recursionDepth", 3)
maya.cmds.setAttr("defaultRenderGlobals.imageFormat", 23)
maya.cmds.setAttr("defaultRenderGlobals.startFrame", 10)
