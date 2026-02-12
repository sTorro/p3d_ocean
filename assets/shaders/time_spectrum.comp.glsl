/*
 * time_spectrum.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Compute shader for generating time-varying spectrum from phases + initial spectrum
 *              Generate time-varying spectrum from phases + initial spectrum
 *              Output is RGBA32F where:
 *                  xy = complex(h_x + i*h)
 *                  zw = complex(h_z)
 */

#version 430

#define PI 3.14159265359

layout (local_size_x = 32, local_size_y = 32) in;

layout(r32f) uniform readonly image2D u_phases;            // R32F
layout(r32f) uniform readonly image2D u_initial_spectrum;  // R32F
layout(rgba32f) uniform writeonly image2D u_spectrum;      // RGBA32F

uniform int u_resolution;
uniform int u_ocean_size;
uniform float u_choppiness;

vec2 multiply_complex(vec2 a, vec2 b)
{
    return vec2(a.x * b.x - a.y * b.y, a.y * b.x + a.x * b.y);
}

vec2 multiply_by_i(vec2 z)
{
    return vec2(-z.y, z.x);
}

void main()
{
    ivec2 pixel_coord = ivec2(gl_GlobalInvocationID.xy);
    if (pixel_coord.x >= u_resolution || pixel_coord.y >= u_resolution) {
        return;
    }

    float half_res = 0.5 * float(u_resolution);
    float n = (float(pixel_coord.x) < half_res) ? float(pixel_coord.x) : float(pixel_coord.x) - float(u_resolution);
    float m = (float(pixel_coord.y) < half_res) ? float(pixel_coord.y) : float(pixel_coord.y) - float(u_resolution);

    vec2 wave_vector = (2.0 * PI * vec2(n, m)) / float(u_ocean_size);
    float k = length(wave_vector);

    float phase = imageLoad(u_phases, pixel_coord).r;
    vec2 phase_vector = vec2(cos(phase), sin(phase));

    // Initial spectrum is stored as real amplitude in R.
    vec2 h0 = vec2(imageLoad(u_initial_spectrum, pixel_coord).r, 0.0);

    // Conjugate term from mirrored coordinate: h0*(-k).
    ivec2 mirror_coord = ivec2(
        (u_resolution - pixel_coord.x) % u_resolution,
        (u_resolution - pixel_coord.y) % u_resolution
    );
    vec2 h0_star = vec2(imageLoad(u_initial_spectrum, mirror_coord).r, 0.0);
    h0_star.y *= -1.0;

    vec2 h = multiply_complex(h0, phase_vector) + multiply_complex(h0_star, vec2(phase_vector.x, -phase_vector.y));

    vec2 h_x = vec2(0.0);
    vec2 h_z = vec2(0.0);

    if (k > 1e-6) {
        h_x = -multiply_by_i(h * (wave_vector.x / k)) * u_choppiness;
        h_z = -multiply_by_i(h * (wave_vector.y / k)) * u_choppiness;
    }

    // No DC term
    if (k <= 1e-6) {
        h = vec2(0.0);
        h_x = vec2(0.0);
        h_z = vec2(0.0);
    }

    imageStore(u_spectrum, pixel_coord, vec4(h_x + multiply_by_i(h), h_z));
}
