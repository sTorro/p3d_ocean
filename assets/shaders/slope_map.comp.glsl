/*
 * slope_map.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Compute shader for generating slope/normal map from displacement map
 *              Generate a slope/normal map from the displacement map
 *              This matches the OceanFFT CS_NormalMap.comp, adapted to our coordinate system:
 *                  - Ocean grid lies on the X-Y plane, with +Z up
 *                  - Displacement map stores xyz = (Dx, height, Dz) but in our world it's (Dx, Dy, Dz)?
 *                    Here we interpret displacement.xyz as offsets in (X, Z(up), Y)??
 *                    For now: treat displacement.xyz as (X offset, height (Z), Y offset)
 *
 *              Output: RGBA32F where xyz = unit normal
 */

#version 430


layout (local_size_x = 32, local_size_y = 32) in;

layout(rgba32f) uniform readonly image2D u_displacement;
layout(rgba32f) uniform writeonly image2D u_slope_map;

uniform int u_resolution;
uniform int u_ocean_size;

vec3 disp_at(ivec2 c)
{
    return imageLoad(u_displacement, c).xyz;
}

void main()
{
    ivec2 c = ivec2(gl_GlobalInvocationID.xy);
    if (c.x >= u_resolution || c.y >= u_resolution) {
        return;
    }

    float texel = 1.0 / float(u_resolution);
    float texel_size = float(u_ocean_size) * texel;

    ivec2 cr = ivec2(min(c.x + 1, u_resolution - 1), c.y);
    ivec2 cl = ivec2(max(c.x - 1, 0), c.y);
    ivec2 cu = ivec2(c.x, min(c.y + 1, u_resolution - 1));
    ivec2 cd = ivec2(c.x, max(c.y - 1, 0));

    // Displacement is encoded as (dx, height, dz) in the displacement map.
    // Our ocean grid is on X-Y with Z up, so interpret:
    //   X offset = dx
    //   Y offset = dz
    //   Z offset = height
    vec3 center_d = disp_at(c);
    vec3 center = vec3(center_d.x, center_d.z, center_d.y);

    vec3 right_d = disp_at(cr);
    vec3 left_d  = disp_at(cl);
    vec3 up_d    = disp_at(cu);
    vec3 down_d  = disp_at(cd);

    vec3 right = vec3(texel_size, 0.0, 0.0) + vec3(right_d.x, right_d.z, right_d.y) - center;
    vec3 left  = vec3(-texel_size, 0.0, 0.0) + vec3(left_d.x, left_d.z, left_d.y) - center;
    vec3 up    = vec3(0.0, texel_size, 0.0) + vec3(up_d.x, up_d.z, up_d.y) - center;
    vec3 down  = vec3(0.0, -texel_size, 0.0) + vec3(down_d.x, down_d.z, down_d.y) - center;

    vec3 up_right = cross(right, up);
    vec3 up_left = cross(up, left);
    vec3 down_left = cross(left, down);
    vec3 down_right = cross(down, right);

    vec3 n_sum = up_right + up_left + down_right + down_left;
    float n_len = length(n_sum);

    // Guard against degenerate (near-zero) vectors that produce NaN after normalize
    // NaN normals propagate through lighting math and show up as black dots/stains
    vec3 n = (n_len > 1e-8) ? (n_sum / n_len) : vec3(0.0, 0.0, 1.0);

    // Ensure it points up-ish.
    if (n.z < 0.0) {
        n = -n;
    }

    imageStore(u_slope_map, c, vec4(n, 1.0));
}
