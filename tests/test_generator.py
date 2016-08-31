import os


def test_generate(temp_app, resources):
    from pydgeot.generator import Generator

    resources.copy('test_generator/source_app', temp_app.root)

    gen = Generator(temp_app)
    gen.generate()

    assert resources.equal('test_generator/expected_build_generate', temp_app.build_root)


def test_delete(temp_app, resources):
    from pydgeot.generator import Generator

    resources.copy('test_generator/source_app', temp_app.root)

    gen = Generator(temp_app)
    gen.generate()

    os.unlink(os.path.join(temp_app.source_root, 'sub/subindex.txt'))

    gen.generate()

    assert resources.equal('test_generator/expected_build_delete', temp_app.build_root)
