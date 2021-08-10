# pytest

from click.testing import CliRunner
from ccs.cli import ccs

def test_upload():
    runner = CliRunner()
    result = runner.invoke(ccs, ['drive', 'upload', '~/images/custom-cd69.iso'])
    assert result.exit_code == 0
    assert result.output == 'foo'

