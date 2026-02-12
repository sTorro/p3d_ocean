/*
 * debug_tex.vert.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Vertex shader for debug texture visualization (passes through UVs)
 */

#version 430

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

uniform mat4 p3d_ModelViewProjectionMatrix;

out vec2 v_uv;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    v_uv = p3d_MultiTexCoord0;
}
