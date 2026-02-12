/*
 * debug_tex.frag.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Debug texture visualization shader
 */

#version 430

uniform sampler2D p3d_Texture0;
uniform float u_gain;
uniform int u_mode;

in vec2 v_uv;
out vec4 frag_color;


void main() {
    vec4 t = texture(p3d_Texture0, v_uv);

    // Mode 0: visualize +R (log-mapped)
    // Mode 1: visualize |RG| magnitude (log-mapped) - good for complex spectra
    // Mode 2: visualize |RGB| magnitude (log-mapped) - vector magnitude
    // Mode 3: visualize phase in [0, 2pi) as [0, 1] (no log)
    // Mode 4: visualize displacement height |G| (log-mapped)
    // Mode 5: visualize normal map (RGB = 0.5*n+0.5)
    float v;
    if (u_mode == 5) {
        vec3 n = normalize(t.xyz);
        frag_color = vec4(n * 0.5 + 0.5, 1.0);
        return;
    }
    if (u_mode == 3) {
        const float two_pi = 6.28318530718;
        v = fract(t.r / two_pi);
        frag_color = vec4(vec3(v), 1.0);
        return;
    } else if (u_mode == 4) {
        v = abs(t.g);
    } else if (u_mode == 2) {
        v = length(t.rgb);
    } else if (u_mode == 1) {
        v = length(t.rg);
    } else {
        v = max(t.r, 0.0);
    }

    float x = v * u_gain;
    float g = log(1.0 + x) / log(1.0 + u_gain);
    g = clamp(g, 0.0, 1.0);
    frag_color = vec4(vec3(g), 1.0);
}
