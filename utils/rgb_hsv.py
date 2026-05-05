import numpy as np

def fromHSV_toRGB(h,s,v):
    if s:
        if h == 1.0: h = 0.0
        i = int(h*6.0); f = h*6.0 - i
        
        w = int(255*( v * (1.0 - s) ))
        q = int(255*( v * (1.0 - s * f) ))
        t = int(255*( v * (1.0 - s * (1.0 - f)) ))
        v = int(255*v)
        
        if i==0: return [v, t, w]
        if i==1: return [q, v, w]
        if i==2: return [w, v, t]
        if i==3: return [w, q, v]
        if i==4: return [t, w, v]
        if i==5: return [v, w, q]
    else: v = int(255*v); return [v, v, v]
       
def fromRGB_toHSV(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0:
        s = 0
    else:
        s = (df/mx)*100
    v = mx*100
    return h, s, v

def fromHSV_toRGB_vectorized(h, s, v, out=None):
    """
    Vectorized HSV to RGB conversion using NumPy.
    h, s, v can be scalars or arrays.
    Returns RGB array of shape (..., 3) in range [0, 255]
    """
    h, s, v = np.broadcast_arrays(np.atleast_1d(h), np.atleast_1d(s), np.atleast_1d(v))

    h_6 = (h % 1.0) * 6.0
    i = np.floor(h_6).astype(np.int32)
    f = h_6 - i
    
    v_255 = v * 255.0
    
    w = (v_255 * (1.0 - s)).astype(np.int32)
    q = (v_255 * (1.0 - s * f)).astype(np.int32)
    t = (v_255 * (1.0 - s * (1.0 - f))).astype(np.int32)
    v_255 = v_255.astype(np.int32)

    if out is None:
        rgb = np.zeros(h.shape + (3,), dtype=np.int32)
    else:
        rgb = out

    cond = i == 0
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = v_255[cond], t[cond], w[cond]
    
    cond = i == 1
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = q[cond], v_255[cond], w[cond]
    
    cond = i == 2
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = w[cond], v_255[cond], t[cond]
    
    cond = i == 3
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = w[cond], q[cond], v_255[cond]
    
    cond = i == 4
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = t[cond], w[cond], v_255[cond]
    
    cond = i == 5
    rgb[cond, 0], rgb[cond, 1], rgb[cond, 2] = v_255[cond], w[cond], q[cond]
    
    # Handle saturation == 0
    s_zero = (s == 0)
    rgb[s_zero, 0] = v_255[s_zero]
    rgb[s_zero, 1] = v_255[s_zero]
    rgb[s_zero, 2] = v_255[s_zero]
    
    return rgb
