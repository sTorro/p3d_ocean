/*
 * unpack_displacement.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Compute shader for unpacking IFFT complex output into a displacement map
 *              Generates displacement map from IFFT complex output
 *              Unpack IFFT complex output into a displacement map:
 *                  Input: RGBA32F where
 *                      xy = complex sequence0  (after IFFT: real=Dx, imag=height)
 *                      zw = complex sequence1  (after IFFT: real=Dz, imag~0)
 *                  Output: RGBA32F displacement map with xyz = (Dx, height, Dz)
 */

#version 430

layout (local_size_x = 32, local_size_y = 32) in;

layout(rgba32f) uniform readonly image2D u_ifft;          // IFFT output (packed complex)
layout(rgba32f) uniform writeonly image2D u_displacement; // displacement map

uniform int u_resolution;

void main()
{
    ivec2 pixel_coord = ivec2(gl_GlobalInvocationID.xy);
    if (pixel_coord.x >= u_resolution || pixel_coord.y >= u_resolution) {
        return;
    }

    vec4 t = imageLoad(u_ifft, pixel_coord);

    float dx = t.x; // real(seq0)
    float h  = t.y; // imag(seq0)
    float dz = t.z; // real(seq1)

    imageStore(u_displacement, pixel_coord, vec4(dx, h, dz, 1.0));
}
