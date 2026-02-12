/*
 * fft_horizontal.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: IFFT horizontal pass compute shader (butterfly stages)
 *              Ported from the OceanFFT project, but uses rgba32f images to match our Texture.F_rgba32.
 */

#version 430

#define PI 3.14159265358979323846

layout (local_size_x = 256, local_size_y = 1, local_size_z = 1) in;

layout(rgba32f) uniform readonly image2D u_input;
layout(rgba32f) uniform writeonly image2D u_output;

uniform int u_total_count;
uniform int u_subseq_count;

vec2 multiply_complex(vec2 a, vec2 b)
{
    return vec2(a.x * b.x - a.y * b.y, a.y * b.x + a.x * b.y);
}

vec4 butterfly_operation(vec2 a, vec2 b, vec2 twiddle)
{
    vec2 twiddle_b = multiply_complex(twiddle, b);
    return vec4(a + twiddle_b, a - twiddle_b);
}

void main()
{
    // Dispatch model:
    // - X dimension covers butterfly threads (thread_idx in [0, u_total_count/2))
    // - Y dimension selects the row
    int thread_count = u_total_count >> 1;
    int thread_idx = int(gl_GlobalInvocationID.x);
    int row = int(gl_WorkGroupID.y);

    if (thread_idx >= thread_count) {
        return;
    }

    int in_idx = thread_idx & (u_subseq_count - 1);
    int out_idx = ((thread_idx - in_idx) << 1) + in_idx;

    float angle = -PI * (float(in_idx) / float(u_subseq_count));
    vec2 twiddle = vec2(cos(angle), sin(angle));

    vec4 a = imageLoad(u_input, ivec2(thread_idx, row));
    vec4 b = imageLoad(u_input, ivec2(thread_idx + thread_count, row));

    // Two complex sequences in one vec4: (a.xy) and (a.zw)
    vec4 result0 = butterfly_operation(a.xy, b.xy, twiddle);
    vec4 result1 = butterfly_operation(a.zw, b.zw, twiddle);

    imageStore(u_output, ivec2(out_idx, row), vec4(result0.xy, result1.xy));
    imageStore(u_output, ivec2(out_idx + u_subseq_count, row), vec4(result0.zw, result1.zw));
}
