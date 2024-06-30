""" Custom port of librosa trim code, to remove numba dependency. 
This allows us to use librosa.trim effect without the librosa or numba dependancy.

All code below adapted from librosa open source github:
"""

import numpy as np
import torch
import torch.nn.functional as F
import warnings


def amplitude_to_db(S, ref=1.0, amin=1e-5, top_db=80.0):
    """Convert an amplitude spectrogram to dB-scaled spectrogram.

    This is equivalent to ``power_to_db(S**2)``, but is provided for convenience.

    Parameters
    ----------
    S : np.ndarray
        input amplitude

    ref : scalar or callable
        If scalar, the amplitude ``abs(S)`` is scaled relative to ``ref``:
        ``20 * log10(S / ref)``.
        Zeros in the output correspond to positions where ``S == ref``.

        If callable, the reference value is computed as ``ref(S)``.

    amin : float > 0 [scalar]
        minimum threshold for ``S`` and ``ref``

    top_db : float >= 0 [scalar]
        threshold the output at ``top_db`` below the peak:
        ``max(20 * log10(S)) - top_db``


    Returns
    -------
    S_db : np.ndarray
        ``S`` measured in dB

    See Also
    --------
    power_to_db, db_to_amplitude

    Notes
    -----
    This function caches at level 30.
    """

    # S = np.asarray(S)
    S = torch.asarray(S)
    

    magnitude = S.abs()

    if callable(ref):
        # User supplied a function to calculate reference power
        ref_value = ref(magnitude)
    else:
        ref_value = torch.abs(ref)

    power = torch.square(magnitude, out=magnitude)

    return power_to_db(power, ref=ref_value ** 2, amin=amin ** 2, top_db=top_db)


def _signal_to_frame_nonsilent(
    y, frame_length=2048, hop_length=512, top_db=60, ref=torch.max
):
    """Frame-wise non-silent indicator for audio input.

    This is a helper function for `trim` and `split`.

    Parameters
    ----------
    y : np.ndarray, shape=(n,) or (2,n)
        Audio signal, mono or stereo

    frame_length : int > 0
        The number of samples per frame

    hop_length : int > 0
        The number of samples between frames

    top_db : number > 0
        The threshold (in decibels) below reference to consider as
        silence

    ref : callable or float
        The reference power

    Returns
    -------
    non_silent : np.ndarray, shape=(m,), dtype=bool
        Indicator of non-silent frames
    """
    # Convert to mono
    if y.ndim > 1:
        y_mono = torch.mean(y, dim=0)
    else: y_mono = y

    # Compute the MSE for the signal
    mse = rms(y=y_mono, frame_length=frame_length, hop_length=hop_length) ** 2
    
    return power_to_db(mse.squeeze(), ref=ref, top_db=None) > -top_db


def trim(y, top_db=60, ref=torch.max, frame_length=2048, hop_length=512):
    """Trim leading and trailing silence from an audio signal.

    Parameters
    ----------
    y : np.ndarray, shape=(n,) or (2,n)
        Audio signal, can be mono or stereo

    top_db : number > 0
        The threshold (in decibels) below reference to consider as
        silence

    ref : number or callable
        The reference power.  By default, it uses `np.max` and compares
        to the peak power in the signal.

    frame_length : int > 0
        The number of samples per analysis frame

    hop_length : int > 0
        The number of samples between analysis frames

    Returns
    -------
    y_trimmed : np.ndarray, shape=(m,) or (2, m)
        The trimmed signal

    index : np.ndarray, shape=(2,)
        the interval of ``y`` corresponding to the non-silent region:
        ``y_trimmed = y[index[0]:index[1]]`` (for mono) or
        ``y_trimmed = y[:, index[0]:index[1]]`` (for stereo).


    Examples
    --------
    >>> # Load some audio
    >>> y, sr = librosa.load(librosa.ex('choice'))
    >>> # Trim the beginning and ending silence
    >>> yt, index = librosa.effects.trim(y)
    >>> # Print the durations
    >>> print(librosa.get_duration(y), librosa.get_duration(yt))
    25.025986394557822 25.007891156462584
    """

    non_silent = _signal_to_frame_nonsilent(
        y, frame_length=frame_length, hop_length=hop_length, ref=ref, top_db=top_db
    )

    # nonzero = np.flatnonzero(non_silent)
    nonzero = torch.nonzero(torch.ravel(non_silent)).squeeze()#[0]

    if nonzero.numel() > 0:
        # Compute the start and end positions
        # End position goes one frame past the last non-zero
        start = int(frames_to_samples(nonzero[0], hop_length))
        end = min(y.shape[-1], int(frames_to_samples(nonzero[-1] + 1, hop_length)))
    else:
        # The signal only contains zeros
        start, end = 0, 0

    # Build the mono/stereo index
    full_index = [slice(None)] * y.ndim
    full_index[-1] = slice(start, end)

    # print(non_silent)
    # print(non_silent.shape, nonzero.shape)

    return y[tuple(full_index)], torch.asarray([start, end])


def rms(
    y=None, S=None, frame_length=2048, hop_length=512, center=True, pad_mode="reflect"
):
    """Compute root-mean-square (RMS) value for each frame, either from the
    audio samples ``y`` or from a spectrogram ``S``.

    Computing the RMS value from audio samples is faster as it doesn't require
    a STFT calculation. However, using a spectrogram will give a more accurate
    representation of energy over time because its frames can be windowed,
    thus prefer using ``S`` if it's already available.


    Parameters
    ----------
    y : np.ndarray [shape=(n,)] or None
        (optional) audio time series. Required if ``S`` is not input.

    S : np.ndarray [shape=(d, t)] or None
        (optional) spectrogram magnitude. Required if ``y`` is not input.

    frame_length : int > 0 [scalar]
        length of analysis frame (in samples) for energy calculation

    hop_length : int > 0 [scalar]
        hop length for STFT. See `librosa.stft` for details.

    center : bool
        If `True` and operating on time-domain input (``y``), pad the signal
        by ``frame_length//2`` on either side.

        If operating on spectrogram input, this has no effect.

    pad_mode : str
        Padding mode for centered analysis.  See `numpy.pad` for valid
        values.

    Returns
    -------
    rms : np.ndarray [shape=(1, t)]
        RMS value for each frame


    Examples
    --------
    >>> y, sr = librosa.load(librosa.ex('trumpet'))
    >>> librosa.feature.rms(y=y)
    array([[1.248e-01, 1.259e-01, ..., 1.845e-05, 1.796e-05]],
          dtype=float32)

    Or from spectrogram input

    >>> S, phase = librosa.magphase(librosa.stft(y))
    >>> rms = librosa.feature.rms(S=S)

    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots(nrows=2, sharex=True)
    >>> times = librosa.times_like(rms)
    >>> ax[0].semilogy(times, rms[0], label='RMS Energy')
    >>> ax[0].set(xticks=[])
    >>> ax[0].legend()
    >>> ax[0].label_outer()
    >>> librosa.display.specshow(librosa.amplitude_to_db(S, ref=np.max),
    ...                          y_axis='log', x_axis='time', ax=ax[1])
    >>> ax[1].set(title='log Power spectrogram')

    Use a STFT window of constant ones and no frame centering to get consistent
    results with the RMS computed from the audio samples ``y``

    >>> S = librosa.magphase(librosa.stft(y, window=np.ones, center=False))[0]
    >>> librosa.feature.rms(S=S)
    >>> plt.show()

    """
    if y is not None:
        if y.dim() > 1:
            y = torch.mean(y, dim=0)
        
        if center:
            y = F.pad(y[None, None], (int(frame_length//2), int(frame_length//2)), mode=pad_mode)[0, 0]
            # y = np.pad(y, int(frame_length // 2), mode=pad_mode)

        x = frame(y, frame_length=frame_length, hop_length=hop_length)
        # print(y.shape, x.shape, x)
        # Calculate power
        power = torch.mean(x.abs() ** 2, dim=0, keepdim=True)
    elif S is not None:
        # Check the frame length
        if S.shape[0] != frame_length // 2 + 1:
            raise AssertionError(
                "Since S.shape[0] is {}, "
                "frame_length is expected to be {} or {}; "
                "found {}".format(
                    S.shape[0], S.shape[0] * 2 - 2, S.shape[0] * 2 - 1, frame_length
                )
            )

        # power spectrogram
        x = torch.abs(S) ** 2

        # Adjust the DC and sr/2 component
        x[0] *= 0.5
        if frame_length % 2 == 0:
            x[-1] *= 0.5

        # Calculate power
        power = 2 * torch.sum(x, dim=0, keepdim=True) / frame_length ** 2
    else:
        raise AssertionError("Either `y` or `S` must be input.")

    return torch.sqrt(power)


def frame(x, frame_length, hop_length, axis=-1):
    """Slice a data array into (overlapping) frames.

    This implementation uses low-level stride manipulation to avoid
    making a copy of the data.  The resulting frame representation
    is a new view of the same input data.

    However, if the input data is not contiguous in memory, a warning
    will be issued and the output will be a full copy, rather than
    a view of the input data.

    For example, a one-dimensional input ``x = [0, 1, 2, 3, 4, 5, 6]``
    can be framed with frame length 3 and hop length 2 in two ways.
    The first (``axis=-1``), results in the array ``x_frames``::

        [[0, 2, 4],
         [1, 3, 5],
         [2, 4, 6]]

    where each column ``x_frames[:, i]`` contains a contiguous slice of
    the input ``x[i * hop_length : i * hop_length + frame_length]``.

    The second way (``axis=0``) results in the array ``x_frames``::

        [[0, 1, 2],
         [2, 3, 4],
         [4, 5, 6]]

    where each row ``x_frames[i]`` contains a contiguous slice of the input.

    This generalizes to higher dimensional inputs, as shown in the examples below.
    In general, the framing operation increments by 1 the number of dimensions,
    adding a new "frame axis" either to the end of the array (``axis=-1``)
    or the beginning of the array (``axis=0``).


    Parameters
    ----------
    x : np.ndarray
        Array to frame

    frame_length : int > 0 [scalar]
        Length of the frame

    hop_length : int > 0 [scalar]
        Number of steps to advance between frames

    axis : 0 or -1
        The axis along which to frame.

        If ``axis=-1`` (the default), then ``x`` is framed along its last dimension.
        ``x`` must be "F-contiguous" in this case.

        If ``axis=0``, then ``x`` is framed along its first dimension.
        ``x`` must be "C-contiguous" in this case.

    Returns
    -------
    x_frames : np.ndarray [shape=(..., frame_length, N_FRAMES) or (N_FRAMES, frame_length, ...)]
        A framed view of ``x``, for example with ``axis=-1`` (framing on the last dimension)::

            x_frames[..., j] == x[..., j * hop_length : j * hop_length + frame_length]

        If ``axis=0`` (framing on the first dimension), then::

            x_frames[j] = x[j * hop_length : j * hop_length + frame_length]

    Raises
    ------
    ParameterError
        If ``x`` is not an `np.ndarray`.

        If ``x.shape[axis] < frame_length``, there is not enough data to fill one frame.

        If ``hop_length < 1``, frames cannot advance.

        If ``axis`` is not 0 or -1.  Framing is only supported along the first or last axis.


    See Also
    --------
    numpy.asfortranarray : Convert data to F-contiguous representation
    numpy.ascontiguousarray : Convert data to C-contiguous representation
    numpy.ndarray.flags : information about the memory layout of a numpy `ndarray`.

    Examples
    --------
    Extract 2048-sample frames from monophonic signal with a hop of 64 samples per frame

    >>> y, sr = librosa.load(librosa.ex('trumpet'))
    >>> frames = librosa.util.frame(y, frame_length=2048, hop_length=64)
    >>> frames
    array([[-1.407e-03, -2.604e-02, ..., -1.795e-05, -8.108e-06],
           [-4.461e-04, -3.721e-02, ..., -1.573e-05, -1.652e-05],
           ...,
           [ 7.960e-02, -2.335e-01, ..., -6.815e-06,  1.266e-05],
           [ 9.568e-02, -1.252e-01, ...,  7.397e-06, -1.921e-05]],
          dtype=float32)
    >>> y.shape
    (117601,)

    >>> frames.shape
    (2048, 1806)

    Or frame along the first axis instead of the last:

    >>> frames = librosa.util.frame(y, frame_length=2048, hop_length=64, axis=0)
    >>> frames.shape
    (1806, 2048)

    Frame a stereo signal:

    >>> y, sr = librosa.load(librosa.ex('trumpet', hq=True), mono=False)
    >>> y.shape
    (2, 117601)
    >>> frames = librosa.util.frame(y, frame_length=2048, hop_length=64)
    (2, 2048, 1806)

    Carve an STFT into fixed-length patches of 32 frames with 50% overlap

    >>> y, sr = librosa.load(librosa.ex('trumpet'))
    >>> S = np.abs(librosa.stft(y))
    >>> S.shape
    (1025, 230)
    >>> S_patch = librosa.util.frame(S, frame_length=32, hop_length=16)
    >>> S_patch.shape
    (1025, 32, 13)
    >>> # The first patch contains the first 32 frames of S
    >>> np.allclose(S_patch[:, :, 0], S[:, :32])
    True
    >>> # The second patch contains frames 16 to 16+32=48, and so on
    >>> np.allclose(S_patch[:, :, 1], S[:, 16:48])
    True
    """

    # if not isinstance(x, np.ndarray):
    #     raise AssertionError(
    #         "Input must be of type numpy.ndarray, " "given type(x)={}".format(type(x))
    #     )
    x: torch.Tensor = x

    if x.shape[axis] < frame_length:
        raise AssertionError(
            "Input is too short (n={:d})"
            " for frame_length={:d}".format(x.shape[axis], frame_length)
        )

    if hop_length < 1:
        raise AssertionError("Invalid hop_length: {:d}".format(hop_length))

    if axis == -1 and not x.is_contiguous():
        warnings.warn(
            "librosa.util.frame called with axis={} "
            "on a non-contiguous input. This will result in a copy.".format(axis)
        )
        x = x.contiguous()
    elif axis == 0 and not x.is_contiguous():
        warnings.warn(
            "librosa.util.frame called with axis={} "
            "on a non-contiguous input. This will result in a copy.".format(axis)
        )
        x = x.contiguous()

    n_frames = 1 + (x.shape[axis] - frame_length) // hop_length
    strides = torch.asarray(x.numpy().strides)
    # print(strides, x)
    new_stride = torch.prod(strides[strides > 0] // x.itemsize) * x.itemsize

    if axis == -1:
        shape = list(x.shape)[:-1] + [frame_length, n_frames]
        strides = list(strides) + [hop_length * new_stride]

    elif axis == 0:
        shape = [n_frames, frame_length] + list(x.shape)[1:]
        strides = [hop_length * new_stride] + list(strides)

    else:
        raise AssertionError("Frame axis={} must be either 0 or -1".format(axis))

    return torch.from_numpy(as_strided(x, shape=shape, strides=strides))
    # return x.as_strided(size=shape, stride=strides)



class DummyArray:
    """Dummy object that just exists to hang __array_interface__ dictionaries
    and possibly keep alive a reference to a base array.
    """

    def __init__(self, interface, base=None):
        self.__array_interface__ = interface
        self.base = base



def as_strided(x, shape=None, strides=None, subok=False, writeable=True):
    """
    Create a view into the array with the given shape and strides.

    .. warning:: This function has to be used with extreme care, see notes.

    Parameters
    ----------
    x : ndarray
        Array to create a new.
    shape : sequence of int, optional
        The shape of the new array. Defaults to ``x.shape``.
    strides : sequence of int, optional
        The strides of the new array. Defaults to ``x.strides``.
    subok : bool, optional
        .. versionadded:: 1.10

        If True, subclasses are preserved.
    writeable : bool, optional
        .. versionadded:: 1.12

        If set to False, the returned array will always be readonly.
        Otherwise it will be writable if the original array was. It
        is advisable to set this to False if possible (see Notes).

    Returns
    -------
    view : ndarray

    See also
    --------
    broadcast_to : broadcast an array to a given shape.
    reshape : reshape an array.
    lib.stride_tricks.sliding_window_view :
        userfriendly and safe function for the creation of sliding window views.

    Notes
    -----
    ``as_strided`` creates a view into the array given the exact strides
    and shape. This means it manipulates the internal data structure of
    ndarray and, if done incorrectly, the array elements can point to
    invalid memory and can corrupt results or crash your program.
    It is advisable to always use the original ``x.strides`` when
    calculating new strides to avoid reliance on a contiguous memory
    layout.

    Furthermore, arrays created with this function often contain self
    overlapping memory, so that two elements are identical.
    Vectorized write operations on such arrays will typically be
    unpredictable. They may even give different results for small, large,
    or transposed arrays.
    Since writing to these arrays has to be tested and done with great
    care, you may want to use ``writeable=False`` to avoid accidental write
    operations.

    For these reasons it is advisable to avoid ``as_strided`` when
    possible.
    """
    # first convert input to array, possibly keeping subclass
    x = np.array(x, copy=False, subok=subok)
    interface = dict(x.__array_interface__)
    if shape is not None:
        interface['shape'] = tuple(shape)
    if strides is not None:
        interface['strides'] = tuple(strides)

    array = np.asarray(DummyArray(interface, base=x))
    # The route via `__interface__` does not preserve structured
    # dtypes. Since dtype should remain unchanged, we set it explicitly.
    array.dtype = x.dtype

    view = _maybe_view_as_subclass(x, array)

    if view.flags.writeable and not writeable:
        view.flags.writeable = False

    return view


def _maybe_view_as_subclass(original_array, new_array):
    if type(original_array) is not type(new_array):
        # if input was an ndarray subclass and subclasses were OK,
        # then view the result as that subclass.
        new_array = new_array.view(type=type(original_array))
        # Since we have done something akin to a view from original_array, we
        # should let the subclass finalize (if it has it implemented, i.e., is
        # not None).
        if new_array.__array_finalize__:
            new_array.__array_finalize__(original_array)
    return new_array


def power_to_db(S, ref=1.0, amin=1e-10, top_db=80.0):
    """Convert a power spectrogram (amplitude squared) to decibel (dB) units

    This computes the scaling ``10 * log10(S / ref)`` in a numerically
    stable way.

    Parameters
    ----------
    S : np.ndarray
        input power

    ref : scalar or callable
        If scalar, the amplitude ``abs(S)`` is scaled relative to ``ref``::

            10 * log10(S / ref)

        Zeros in the output correspond to positions where ``S == ref``.

        If callable, the reference value is computed as ``ref(S)``.

    amin : float > 0 [scalar]
        minimum threshold for ``abs(S)`` and ``ref``

    top_db : float >= 0 [scalar]
        threshold the output at ``top_db`` below the peak:
        ``max(10 * log10(S)) - top_db``

    Returns
    -------
    S_db : np.ndarray
        ``S_db ~= 10 * log10(S) - 10 * log10(ref)``

    See Also
    --------
    perceptual_weighting
    db_to_power
    amplitude_to_db
    db_to_amplitude

    Notes
    -----
    This function caches at level 30.


    Examples
    --------
    Get a power spectrogram from a waveform ``y``

    >>> y, sr = librosa.load(librosa.ex('trumpet'))
    >>> S = np.abs(librosa.stft(y))
    >>> librosa.power_to_db(S**2)
    array([[-41.809, -41.809, ..., -41.809, -41.809],
           [-41.809, -41.809, ..., -41.809, -41.809],
           ...,
           [-41.809, -41.809, ..., -41.809, -41.809],
           [-41.809, -41.809, ..., -41.809, -41.809]], dtype=float32)

    Compute dB relative to peak power

    >>> librosa.power_to_db(S**2, ref=np.max)
    array([[-80., -80., ..., -80., -80.],
           [-80., -80., ..., -80., -80.],
           ...,
           [-80., -80., ..., -80., -80.],
           [-80., -80., ..., -80., -80.]], dtype=float32)

    Or compare to median power

    >>> librosa.power_to_db(S**2, ref=np.median)
    array([[16.578, 16.578, ..., 16.578, 16.578],
           [16.578, 16.578, ..., 16.578, 16.578],
           ...,
           [16.578, 16.578, ..., 16.578, 16.578],
           [16.578, 16.578, ..., 16.578, 16.578]], dtype=float32)


    And plot the results

    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots(nrows=2, sharex=True, sharey=True)
    >>> imgpow = librosa.display.specshow(S**2, sr=sr, y_axis='log', x_axis='time',
    ...                                   ax=ax[0])
    >>> ax[0].set(title='Power spectrogram')
    >>> ax[0].label_outer()
    >>> imgdb = librosa.display.specshow(librosa.power_to_db(S**2, ref=np.max),
    ...                                  sr=sr, y_axis='log', x_axis='time', ax=ax[1])
    >>> ax[1].set(title='Log-Power spectrogram')
    >>> fig.colorbar(imgpow, ax=ax[0])
    >>> fig.colorbar(imgdb, ax=ax[1], format="%+2.0f dB")
    """

    S = torch.asarray(S)

    if amin <= 0:
        raise AssertionError("amin must be strictly positive")

    # if np.issubdtype(S.dtype, np.complexfloating):
    #     warnings.warn(
    #         "power_to_db was called on complex input so phase "
    #         "information will be discarded. To suppress this warning, "
    #         "call power_to_db(np.abs(D)**2) instead."
    #     )
    #     magnitude = np.abs(S)
    # else:
    magnitude = S

    if callable(ref):
        # User supplied a function to calculate reference power
        ref_value = ref(magnitude)
    else:
        ref_value = torch.abs(ref)

    log_spec = 10.0 * torch.log10(torch.maximum(torch.tensor(amin), magnitude))
    log_spec -= 10.0 * torch.log10(torch.maximum(torch.tensor(amin), ref_value))

    if top_db is not None:
        if top_db < 0:
            raise AssertionError("top_db must be non-negative")
        log_spec = torch.maximum(log_spec, log_spec.max() - top_db)

    return log_spec


def frames_to_samples(frames, hop_length=512, n_fft=None):
    """Converts frame indices to audio sample indices.

    Parameters
    ----------
    frames     : number or np.ndarray [shape=(n,)]
        frame index or vector of frame indices

    hop_length : int > 0 [scalar]
        number of samples between successive frames

    n_fft : None or int > 0 [scalar]
        Optional: length of the FFT window.
        If given, time conversion will include an offset of ``n_fft // 2``
        to counteract windowing effects when using a non-centered STFT.

    Returns
    -------
    times : number or np.ndarray
        time (in samples) of each given frame number::

            times[i] = frames[i] * hop_length

    See Also
    --------
    frames_to_time : convert frame indices to time values
    samples_to_frames : convert sample indices to frame indices

    Examples
    --------
    >>> y, sr = librosa.load(librosa.ex('choice'))
    >>> tempo, beats = librosa.beat.beat_track(y, sr=sr)
    >>> beat_samples = librosa.frames_to_samples(beats)
    """

    offset = 0
    if n_fft is not None:
        offset = int(n_fft // 2)

    return (torch.asarray(frames) * hop_length + offset).to(torch.int)