import couch
from tornado import ioloop, gen

@gen.coroutine
def run_test():
    db = couch.AsyncCouch('mytestdb')
    yield db.create_db()
    r = yield db.save_doc({'msg': 'My first document'})
    doc = yield db.get_doc(r['id'])
    yield db.delete_doc(doc)
    yield db.delete_db()

ioloop.IOLoop.instance.start()
run_test()
ioloop.IOLoop.instance.stop()
