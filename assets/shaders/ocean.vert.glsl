/*
 * ocean.vert.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Vertex shader for rendering the ocean surface
 */

#version 430

in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

uniform sampler2D u_displacement_map;
uniform float u_disp_scale;

out vec3 v_world_pos;
out vec2 v_uv;
out float v_height;   // raw vertical displacement (for SSS / absorption)
out vec4 v_clip_pos;  // clip-space position for screen UVs

void main()
{
    vec2 uv = p3d_MultiTexCoord0;
    vec3 disp = texture(u_displacement_map, uv).xyz; // (dx, height, dz)

    // Our grid is on X-Y with Z up.
    // displacement map is (dx, height, dz) where dz is the horizontal offset along Y.
    vec3 offset = vec3(disp.x, disp.z, disp.y) * u_disp_scale;

    v_height = disp.y * u_disp_scale; // vertical component before swizzle

    vec4 model_pos = vec4(p3d_Vertex.xyz + offset, 1.0);
    v_world_pos = (p3d_ModelMatrix * model_pos).xyz;
    v_uv = uv;

    gl_Position = p3d_ModelViewProjectionMatrix * model_pos;
    v_clip_pos = gl_Position;
}
