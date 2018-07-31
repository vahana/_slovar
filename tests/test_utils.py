import pytest

class TestUtils(object):

    def test_maybe_dotted(self):
        from slovar.utils import maybe_dotted

        with pytest.raises(ImportError):
            maybe_dotted('aa')

        with pytest.raises(ValueError):
            maybe_dotted('')

        with pytest.raises(ValueError):
            maybe_dotted('.view')

        import slovar
        assert maybe_dotted('slovar.utils') == slovar.utils
        assert maybe_dotted('slovar.utils:maybe_dotted') == slovar.utils.maybe_dotted

        maybe_dotted('XYZ', throw=False)
