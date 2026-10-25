"""Pure synthetic decisions; no Git, credentials, network or live401 injection."""
import unittest
from git_publish_verified import publication_action,optional_comment_outcome
class PublicationContracts(unittest.TestCase):
 def test_after_push_resume_is_same_commit_verification_only(self):
  commit='a'*40;state=dict(commit=commit,push_attempted=True,push_confirmed=True)
  self.assertEqual(publication_action(state,commit,'b'*40),'verify_only')
  self.assertEqual(state['commit'],commit)
 def test_optional_401_preserves_scientific_success(self):
  result=optional_comment_outcome('published_readback_verified',401)
  self.assertEqual(result['status'],'published_readback_verified')
  self.assertEqual(result['comment_status'],'pending')
if __name__=='__main__':unittest.main()
