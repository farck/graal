/*
 * Copyright (c) 2013, 2017, Oracle and/or its affiliates. All rights reserved.
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
 *
 * This code is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 2 only, as
 * published by the Free Software Foundation.  Oracle designates this
 * particular file as subject to the "Classpath" exception as provided
 * by Oracle in the LICENSE file that accompanied this code.
 *
 * This code is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * version 2 for more details (a copy is included in the LICENSE file that
 * accompanied this code).
 *
 * You should have received a copy of the GNU General Public License version
 * 2 along with this work; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 */
package org.graalvm.nativeimage;

import org.graalvm.word.PointerBase;

/**
 * Contains static methods for memory allocation in the stack frame.
 *
 * @since 1.0
 */
public final class StackValue {

    private StackValue() {
    }

    /**
     * Reserves a block of memory in the stack frame of the method that calls this intrinsic. The
     * returned pointer is aligned on a word boundary. If the requested size is 0, the method
     * returns {@code null}. The size must be a compile time constant. If the call to this method is
     * in a loop, always the same pointer is returned. In other words: this method does not allocate
     * memory; it returns the address of a fixed-size block of memory that is reserved in the stack
     * frame when the method starts execution. The memory is not initialized. Two distinct calls of
     * this method return different pointers.
     *
     * @since 1.0
     */
    @SuppressWarnings("unused")
    public static <T extends PointerBase> T get(int size) {
        throw new IllegalStateException("Cannot invoke method during native image generation");
    }

    /**
     * Utility method that performs size arithmetic, otherwise equivalent to {@link #get(int)}.
     *
     * @since 1.0
     */
    @SuppressWarnings("unused")
    public static <T extends PointerBase> T get(int numberOfElements, int elementSize) {
        throw new IllegalStateException("Cannot invoke method during native image generation");
    }
}
