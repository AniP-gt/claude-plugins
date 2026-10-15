# RSpec Style Detection

Read `spec/spec_helper.rb`, `spec/rails_helper.rb`, `spec/support/**`, `.rspec`, and 2 to 3 specs near the target. Record each item below as the project does it, with one file reference.

## What to record

- **Location and type**: `spec/models`, `spec/requests` versus `spec/controllers`, `spec/system` versus `spec/features`, `spec/services`, and whether `type:` is inferred (`infer_spec_type_from_file_location!`).
- **Grouping**: `describe '#method'` and `describe '.class_method'`, `context 'when ...'` / `'with ...'` wording, nesting depth, and whether the description is in English or Japanese.
- **Subject and setup**: `subject`, named subject, `let` versus `let!`, `before` blocks, and instance variables (avoid adding them if the project does not use them).
- **Data**: FactoryBot (`create` versus `build` versus `build_stubbed`), traits, `create_list`, fixtures, and how associations are built.
- **Doubles**: `instance_double` / verifying doubles versus `double`, `allow(...).to receive`, `have_received`, WebMock or VCR for HTTP, `travel_to` or Timecop for time, `ActiveJob::TestHelper` / `have_enqueued_job`, `ActionMailer::Base.deliveries` / `have_enqueued_mail`.
- **Assertions**: `expect { }.to change { }`, `have_attributes`, `match_array`, `aggregate_failures`, custom matchers in `spec/support`.
- **Shared code**: `shared_examples` / `it_behaves_like`, `shared_context`, helper modules included by type.
- **Varying inputs**: put the values that change between contexts in their own `let` (`let(:dose) { 3 }`) and override only that `let` in each context, instead of redefining the whole object. The reader then sees what each context changes.
- **One expectation per example or several**: follow the project.
- **DB strategy**: transactional fixtures versus DatabaseCleaner; affects tests that use threads or `after_commit`.

## Run command

Use the project's runner (`bin/rspec`, `bundle exec rspec`, or a script in `Makefile` / `package.json`) with the file path and, for one example, the line number: `bundle exec rspec spec/models/order_spec.rb:42`.

## Common pitfalls

- `let!` creating records that other examples in the group do not need.
- `before(:all)` / `before_all` state leaking between examples.
- Stubbing the method under test (`allow(subject).to receive(...)`).
- Time-dependent specs without frozen time.
- `after_commit` callbacks not firing under transactional fixtures (check the Rails version and project settings).
