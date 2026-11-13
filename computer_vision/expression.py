def detect_expression(blendshapes):
    """Maps MediaPipe ARKit blendshapes to your 5 target expressions."""
    smile = blendshapes.get("mouthSmileLeft", 0) + blendshapes.get("mouthSmileRight", 0)
    frown = blendshapes.get("mouthFrownLeft", 0) + blendshapes.get("mouthFrownRight", 0)
    jaw_open = blendshapes.get("jawOpen", 0)
    brow_raised = (blendshapes.get("browOuterUpLeft", 0) + blendshapes.get("browOuterUpRight", 0)) / 2
    brow_down = (blendshapes.get("browDownLeft", 0) + blendshapes.get("browDownRight", 0)) / 2
    nose_scrunched = (blendshapes.get("noseSneerLeft", 0) + blendshapes.get("noseSneerRight", 0)) / 2

    if jaw_open > 0.4 and brow_raised > 0.3:
        return "surprise"
    elif brow_down >= 0.2 and smile < 0.2:
        return "anger"
    elif smile > 0.6:
        return "happy"
    elif frown > 0.6 or (brow_raised > 0.3 and smile < 0.1):
        return "sad"
    else:
        return "neutral"
